# Import python libraries
import networkx as nx
import itertools as it
import argparse
import random
import queue
import sys

# Import RapidChiplet files
import helpers as hlp
import routing_utils as utils

#########################################################################################################
# Routing algorithms
#########################################################################################################

# The fact that we always use the shortest path with the lowest next-hop-id results in deterministic,
# deadlock-free routing. However, the path diversity is not exploited, and congestion may occur.
# Consider all chiplets as lower-id than all interposer-routers.
def shortest_path_lowest_id_first_routing(ici_graph):	
	# Input: ICI graph
	nodes = ici_graph["nodes"]
	relay_map = ici_graph["relay_map"]
	adj_list = ici_graph["adj_list"]
	chiplets = [x for x in nodes if x[0] == "chiplet"]
	# Output: One routing table for each node. Only chiplets are possible destinations.
	routing_table = {node : {dst : None for dst in chiplets} for node in nodes}
	# Run Dijkstra's algorithm. Only use chiplets as possible destinations.
	for dst in chiplets:
		dists = {node : float("inf") for node in nodes}
		nexts = {node : None for node in nodes}
		todo = queue.PriorityQueue()	
		# Start from the destination
		dists[dst] = 0
		todo.put((0, dst))
		# Explore the graph
		while not todo.empty():
			(cur_dist, cur_node) = todo.get()
			# Skip if we have already found a shorter path to the current node
			if cur_dist > dists[cur_node]:
				continue
			# Iterate over neighbors of the current node
			for nei_node in adj_list[cur_node]:
				nei_dist = cur_dist + 1
				# If we found a shorter path from the neighbor to the destination
				# or an equally long path but over an interposer-router
				# or a path of equal length and component-type but with a lower id
				if (nei_dist < dists[nei_node]) or ((nei_dist == dists[nei_node]) and 
				   (((nexts[nei_node][0] == "chiplet") and (cur_node[0] == "irouter")) or
				   ((nexts[nei_node][0] == cur_node[0]) and (nexts[nei_node][1] > cur_node[1])))):
					dists[nei_node] = nei_dist
					nexts[nei_node] = cur_node
					# If the neighbor node can relay traffic, add it to the queue
					if relay_map[nei_node]:
						todo.put((nei_dist, nei_node))
		# Verify that all nodes have a valid path to the destination and construct the routing table
		for node in nodes:
			if node != dst:
				if nexts[node] is None:
					print("ERROR: Unable to find a path from node %s to node %s" % (str(node), str(dst)))
				else:
					routing_table[node][dst] = nexts[node]
	return {"type" : "default", "table" : routing_table}

def shortest_path_turn_model_random(ici_graph):
	# Create a directed graph for the shortest path computations
	G = nx.DiGraph()
	#also create undirected graph containing only the vertices with forwarding capacity to compute the forbidden turns set on.
	G_SCB = nx.Graph()

	# contains list of non forwarding chiplets
	non_forwarding = []
	# contains list of chiplets
	chiplets = []
	# contains list of all nodes in network
	nodes = []

	#The following 3 for-loops are used to fill up the graphs and lists defined above
	num_vertices= len(ici_graph['nodes'])
	for i in ici_graph['nodes']:
		nodes.append(i)
		G.add_node(i)
		# SCB only considers the forwarding routers
		if i[0] == 'irouter':
			G_SCB.add_node(i)
		else:
			chiplets.append(i)

	#add src and sink
	src = ('',num_vertices)
	sink = ('',num_vertices+1)

	#  add connections to from src sink for chiplet nodes.
	for i in ici_graph['relay_map'].keys():
		G.add_edge(src,i)
		G.add_edge(i, sink)
		if ici_graph['relay_map'][i] == True:
			G_SCB.add_node(i)
		else:
			non_forwarding.append(i)

	#add edges from adj list:
	for i in ici_graph['adj_list'].keys():
		for j in ici_graph['adj_list'][i]:
			G.add_edge(i, j)
			G.add_edge(j, i)
			if i in G_SCB.nodes() and j in G_SCB.nodes():
				G_SCB.add_edge(i,j)

	#compute the cycle breaking set for G_SCB
	forbidden_turns = []
	utils.simple_cycle_breaking(G_SCB, forbidden_turns)
	#generate the linegraph 
	LG =utils.generate_line_graph(G)

	#now remove forbidden turns and turns around non forwarding vertices
	to_remove = []
	for (e1,e2) in LG.edges:
		if (e1,e2) in forbidden_turns or (e1[1] in non_forwarding and e1[0] != src and e2[1] != sink ):
			to_remove.append((e1,e2))

	LG.remove_edges_from(to_remove)

	#now compute shortest paths from to all chiplets
	pred_map= {}
	utils.get_shortest_valid_paths(LG, chiplets, src, pred_map)

	#now compute the routing table

	#just so the neighbors are correct again
	G.remove_node(src)
	G.remove_node(sink)

	#routing table format is: routing_table[source][destination][previous] -> next_hop
	# notably:
	#   - no routing table entry to route from node i to node i.
	#   - when packets are injected into the network, they have prev = -1 
	routing_table = {node : {dst : {} for dst in [c for c in chiplets if c != node]} for node in nodes}

	for u in chiplets:
		for v in chiplets:
			# first clause covers the case, when there is no path from u to v in the network (as then we have no RT entry)
			if u == v or (v,sink) not in pred_map[u].keys():
				pass
			# if there is a path, we use the pred_map as a reverse_pred map and set the next hops until we arrive at u or 
			# until we find an entry in the routing table for the rest of the path.
			else:
				goal = (src,u)
				curr = (v,sink)
				# wait until we reach u
				while curr[0] != goal[1]:
					next = random.choice(pred_map[u][curr])
					first = curr[1]
					second = curr[0]
					third = next[0]
					if first ==sink:
						routing_table[second][u][-1] = third
					else:
						if first not in routing_table[second][u].keys():
							routing_table[second][u][first] = third
						else:
							# or if routing table already contains an entry, rest of path is already fixed.
							break
					curr = next
	return {"type" : "extended", "table" : routing_table}

def generate_routing(chiplets, placement, topology, routing_algorithm):
	# Construct ICI graph
	ici_graph = hlp.construct_ici_graph(chiplets, placement, topology)
	# Construct routing table
	if routing_algorithm == "splif":
		routing_table = shortest_path_lowest_id_first_routing(ici_graph)
	elif routing_algorithm == "sptmr":
		routing_table = shortest_path_turn_model_random(ici_graph)
	else:
		print("ERROR: Unknown routing algorithm: %s" % routing_algorithm)
		sys.exit(1)
	# Store results
	return routing_table

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file")
	parser.add_argument("-rtf", "--routing_table_file", required = True, help = "Name of the routing table file (is stored in ./inputs/routing_tables)")
	parser.add_argument("-ra", "--routing_algorithm", required = True, help = "Routing algorithm to use. Options: splif")
	args = parser.parse_args()
	# Read input files
	design = hlp.read_json(filename = args.design_file)
	chiplets = hlp.read_json(filename = design["chiplets"])
	placement = hlp.read_json(filename = design["placement"])
	topology = hlp.read_json(filename = design["topology"])
	# Generate routing table
	routing_table = generate_routing(chiplets, placement, topology, args.routing_algorithm)
	# Write routing
	hlp.write_json("./inputs/routing_tables/%s.json" % args.routing_table_file, routing_table)

