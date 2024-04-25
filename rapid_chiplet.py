# Import python libraries
import time
import math
import copy
import queue
import argparse
import random as rnd

# Import RapidChiplet files
import helpers as hlp
import validation as vld

# Compute the area summary
def compute_area_summary(chiplets, placement):
	total_chiplet_area = 0
	# Smallest and largest coordinates occupied by a chiplet
	(minx, miny, maxx, maxy) = (float("inf"),float("inf"),-float("inf"),-float("inf"))
	# Iterate through chiplets
	for chiplet_desc in placement["chiplets"]:
		chiplet = chiplets[chiplet_desc["name"]]
		(x,y) = (chiplet_desc["position"]["x"],chiplet_desc["position"]["y"])	# Position
		(w,h) = (chiplet["dimensions"]["x"],chiplet["dimensions"]["y"])			# Dimensions
		# Add this chiplet's are to total area
		total_chiplet_area += (w * h)
		# Update min and max coordinates
		minx = min(minx, x)
		miny = min(miny, y)
		maxx = max(maxx, x + w)
		maxy = max(maxy, y + h)
	# Compute total interposer area
	chip_width = (maxx - minx)
	chip_height = (maxy - miny)
	total_interposer_area =  chip_width * chip_height
	area_summary = {
		"chip_width" : chip_width,	
		"chip_height" : chip_height,	
		"total_chiplet_area" : total_chiplet_area,
		"total_interposer_area" : total_interposer_area
	}
	return area_summary

# Compute the power summary
def compute_power_summary(chiplets, placement, packaging):
	# Compute power consumption of chiplets
	total_chiplet_power = 0
	for chiplet_desc in placement["chiplets"]:
		chiplet = chiplets[chiplet_desc["name"]]
		total_chiplet_power += chiplet["power"]	
	# Compute power consumption of interposer routers
	total_interposer_power = (len(placement["interposer_routers"]) * packaging["power_irouter"]) if packaging["is_active"] else 0
	# Compute total interposer area
	total_power = total_chiplet_power + total_interposer_power 
	power_summary = {
		"total_power" : total_power,
		"total_chiplet_power" : total_chiplet_power,
		"total_interposer_power" : total_interposer_power
	}
	return power_summary

# Compute all link lengths
def compute_link_summary(chiplets, placement, topology, packaging):
	link_lengths = []
	link_lengths_internal = {}
	for link in topology:
		endpoints = [link["ep1"],link["ep2"]]
		# Compute positions of start-and endpoint
		positions = []
		node_ids = []
		for endpoint in endpoints:
			if endpoint["type"] == "chiplet":
				chiplet_desc = placement["chiplets"][endpoint["outer_id"]]
				chiplet = chiplets[chiplet_desc["name"]]
				# Rotate the chiplet if needed	
				chiplet = hlp.rotate_chiplet(chiplet, chiplet_desc["rotation"])
				phy = chiplet["phys"][endpoint["inner_id"]]
				positions.append((chiplet_desc["position"]["x"] + phy["x"],chiplet_desc["position"]["y"] + phy["y"]))
				node_ids.append(endpoint["outer_id"])
			else:
				irouter = placement["interposer_routers"][endpoint["outer_id"]]
				positions.append((irouter["position"]["x"],irouter["position"]["y"]))
				node_ids.append(len(placement["chiplets"]) + endpoint["outer_id"])
		# Compute link length
		if packaging["link_routing"] == "manhattan":
			length = sum([abs(positions[0][dim] - positions[1][dim]) for dim in range(2)])
			link_lengths.append(length)
			link_lengths_internal[tuple(node_ids)] = length
			link_lengths_internal[tuple(reversed(node_ids))] = length
		elif packaging["link_routing"] == "euclidean":
			length =  math.sqrt(sum([abs(positions[0][dim] - positions[1][dim])**2 for dim in range(2)]))
			link_lengths.append(length)
			link_lengths_internal[tuple(node_ids)] = length
			link_lengths_internal[tuple(reversed(node_ids))] = length
	# Summarize link lengths
	link_summary = {
		"avg" : sum(link_lengths) / len(link_lengths),
		"min" : min(link_lengths),
		"max" : max(link_lengths),
		"all" : link_lengths
	}
	return (link_summary, link_lengths_internal)

# Compute the manufacturing cost estimate
def compute_manufacturing_cost(technology, chiplets, placement, packaging, area_summary):
	# First, compute the manufacturing cost per chiplet
	results_per_chiplet = {}
	for chiplet_name in set([x["name"] for x in placement["chiplets"]]):
		results_per_chiplet[chiplet_name] = {}
		chiplet = chiplets[chiplet_name]
		tech = technology[chiplet["technology"]]
		wr = tech["wafer_radius"]										# Wafer radius
		dd = tech["defect_density"]										# Defect density
		wc = tech["wafer_cost"]											# Wafer cost
		ca = chiplet["dimensions"]["x"] * chiplet["dimensions"]["y"]	# Chiplet area
		# Dies per wafer
		dies_per_wafer = int(math.floor(((math.pi * wr**2) / ca) - ((math.pi * 2 * wr) / math.sqrt(2 * ca))))
		results_per_chiplet[chiplet_name]["dies_per_wafer"] = dies_per_wafer
		# Manufacturing yield
		manufacturing_yield = 1.0 / (1.0 + dd * ca)
		results_per_chiplet[chiplet_name]["manufacturing_yield"] = manufacturing_yield
		# Known good dies
		known_good_dies = dies_per_wafer * manufacturing_yield
		results_per_chiplet[chiplet_name]["known_good_dies"] = known_good_dies
		# Cost
		cost = wc / known_good_dies
		results_per_chiplet[chiplet_name]["cost"] = cost
	# Next, compute the manufacturing cost of the interposer if an interposer is used
	results_interposer = {"cost" : 0}
	if packaging["has_interposer"]:
		ip_tech = technology[packaging["interposer_technology"]]
		wr = ip_tech["wafer_radius"]									# Wafer radius
		dd = ip_tech["defect_density"]								# Defect density
		wc = ip_tech["wafer_cost"]									# Wafer cost
		ia = area_summary["total_interposer_area"]						# Interposer area
		# Dies per wafer
		dies_per_wafer = int(math.floor(((math.pi * wr**2) / ia) - ((math.pi * 2 * wr) / math.sqrt(2 * ia))))
		results_interposer["dies_per_wafer"] = dies_per_wafer
		# Manufacturing yield
		manufacturing_yield = 1.0 / (1.0 + dd * ia)
		results_interposer["manufacturing_yield"] = manufacturing_yield
		# Known good dies
		known_good_dies = dies_per_wafer * manufacturing_yield
		results_interposer["known_good_dies"] = known_good_dies
		# Cost
		cost = wc / known_good_dies
		results_interposer["cost"] = cost
	# Compute the overall cost per working chip
	py = packaging["packaging_yield"]									# Packaging yield
	total_cost = (sum([results_per_chiplet[x["name"]]["cost"] for x in placement["chiplets"]]) + results_interposer["cost"]) / py
	return {"total_cost" : total_cost, "interposer" : results_interposer, "chiplets" : results_per_chiplet}

# Constructs a graph where nodes are chiplets and interposer-routers and edges are links.
def construct_ici_graph(chiplets, placement, topology):
	c = len(placement["chiplets"])				# Number of chiplets
	r = len(placement["interposer_routers"])	# Number of interposer-routers
	n = c + r									# Number of nodes in the graph
	# Construct adjacency list
	neighbors = [[] for i in range(n)]
	# Iterate through links
	for link in topology:
		nid1 = (c if link["ep1"]["type"] == "irouter" else 0) + link["ep1"]["outer_id"]
		nid2 = (c if link["ep2"]["type"] == "irouter" else 0) + link["ep2"]["outer_id"]
		neighbors[nid1].append(nid2)
		neighbors[nid2].append(nid1)
	# Collect node attributes...
	relay_map = [None for i in range(n)]
	nodes_by_type = {"C" : [], "M" : [], "I" : []}
	#... for chiplets	
	for nid in range(c):
		chiplet = chiplets[placement["chiplets"][nid]["name"]]
		typ = chiplet["type"][0].upper()
		relay_map[nid] = chiplet["relay"]
		nodes_by_type[typ].append(nid)
	#... for interposer-routers 
	for nid in range(c, c+r):
		relay_map[nid] = True
	# Return graph
	return (c, r, n, neighbors, relay_map, nodes_by_type)

# Computes a full source-destination path for each combination of sending and receiving chiplets in the following
# traffic classes: core->core, core->memory, core->io, memory->io
def construct_ici_routing(ici_graph, routing):
	(c, r, n, neighbors, relay_map, nodes_by_type) = ici_graph
	# Compute a routing per traffic-class.
	classes = ["C2C","C2M","C2I","M2I"]
	# The following two dictionaries are the result of this function - they fully determine the routing
	paths_per_class = {cls : {} for cls in classes}	
	n_paths_per_edge_per_class = {cls : {(src,dst) : 0 for src in range(n) for dst in neighbors[src]} for cls in classes}
	# Cover all traffic classes without running Dijkstra twice on the same start-vertex
	src_types = ["C","M"]	
	dst_types_by_src_type= {"C" : ["C","M","I"], "M" : ["I"]}
	for src_type in src_types:
		# Run Dijkstra for each sending node in a given traffic class
		# We minimize the number of hops, not the latency.
		for src in nodes_by_type[src_type]:
			dist = [float("inf") for i in range(n)]				# Distance from SRC in hops
			preds = [[] for i in range(n)]						# Predecessors (can be many for multiple shortest paths)
			todo = queue.PriorityQueue()						# Visited but not yet processed nodes
			dist[src] = 0
			todo.put((0, src))
			# Explore paths from src to all chiplets
			while todo.qsize() > 0:
				(cur_dist, cur) = todo.get()
				# A shorter path to the cur-node has been found -> skip
				if cur_dist > dist[cur]:
					continue
				# Iterate through neighbors of the cur-node
				for nei in neighbors[cur]:
					nei_dist = cur_dist + 1
					# We found a path to nei that is shorter than the currently best known one
					if nei_dist < dist[nei]:
						dist[nei] = nei_dist
						preds[nei] = [cur]
						# Only enqueue the "nei"-node for processing if it can relay traffic	
						if relay_map[nei]:
							todo.put((nei_dist, nei))
					# We found a path equally short than the shortest path
					elif (routing in ["random","balanced"]) and (nei_dist == dist[nei]) and (cur not in preds[nei]):
						preds[nei].append(cur)
			# Use backtracking to construct all src->dst paths for the given traffic class
			for dst_type in dst_types_by_src_type[src_type]:
				for dst in nodes_by_type[dst_type]:
					cls = src_type + "2" + dst_type
					# Only look at paths with at least one hop
					if dst == src:
						continue
					path = [dst]
					cur = dst		
					while cur != src:
						# Balance paths across links
						if routing == "balanced":
							n_paths = [n_paths_per_edge_per_class[cls][(pred,cur)] for pred in preds[cur]]
							pred = preds[cur][n_paths.index(min(n_paths))]
						# Randomly select shortest paths
						elif routing == "random":
							pred = preds[cur][rnd.randint(0,len(preds[cur])-1)]
						# Use the minimum index (what BookSim does)
						else:
							pred = preds[cur][0]
						n_paths_per_edge_per_class[cls][(pred,cur)] += 1
						cur = pred
						path.insert(0,cur)	
					paths_per_class[cls][(src,dst)] = path
	# Return results
	return (paths_per_class, n_paths_per_edge_per_class)
	
# Compute the proxy for the ICI latency
def compute_ici_latency(technology, chiplets, placement, packaging, ici_graph, ici_routing, link_latencies_internal):
	(c, r, n, neighbors, relay_map, nodes_by_type) = ici_graph
	(paths_per_class, n_paths_per_edge_per_class) = ici_routing
	ici_latencies = {}
	# Dictionary with the latency of relaying a message through a given node
	node_relay_latencies = [(packaging["latency_irouter"] if i >= c else 0) for i in range(n)]
	# Dictionary with latencies of entering/exiting a given node
	node_latencies = [None for i in range(c)]
	# List of dictionaries for edge latencies
	edge_latencies = [{nei : (packaging["link_latency"] if packaging["link_latency_type"] == "constant" else int(math.ceil(eval(packaging["link_latency"])(link_latencies_internal[(i,nei)])))) for nei in neighbors[i]} for i in range(n)]
	# Iterate through chiplets
	for i in range(len(placement["chiplets"])):
		chiplet = chiplets[placement["chiplets"][i]["name"]]
		internal_latency = chiplet["internal_latency"]
		phy_latency = technology[chiplet["technology"]]["phy_latency"]
		node_relay_latencies[i] = internal_latency + 2 * phy_latency
		node_latencies[i] = internal_latency + phy_latency
	# Iterate through traffic classes
	for traffic in ["C2C","C2M","C2I","M2I"]:
		# Compute latencies of all paths in this class
		latencies = []
		for (src,dst) in paths_per_class[traffic]:
			path = paths_per_class[traffic][(src,dst)]
			lat = node_latencies[path[0]]													# Start-node
			lat += sum([node_relay_latencies[path[i]] for i in range(1, len(path)-1)])		# Relaying chiplets
			lat += sum([edge_latencies[path[i]][path[i+1]] for i in range(len(path)-1)]) 	# Link latency
			lat += node_latencies[path[-1]]													# End node
			latencies.append(lat)
		# Compute and store statistics
		ici_latencies[traffic] = {}
		ici_latencies[traffic]["avg"] = sum(latencies) / len(latencies)
		ici_latencies[traffic]["min"] = min(latencies)
		ici_latencies[traffic]["max"] = max(latencies)
		ici_latencies[traffic]["all"] = latencies
	# Return results
	return ici_latencies

# Compute the proxy for the ICI throughput 
def compute_ici_throughput(chiplets, placement, ici_graph, ici_routing):
	(c, r, n, neighbors, relay_map, nodes_by_type) = ici_graph
	(paths_per_class, n_paths_per_edge_per_class) = ici_routing
	ici_throughputs = {}
	# Iterate through traffic classes
	for traffic in ["C2C","C2M","C2I","M2I"]:
		ici_throughputs[traffic] = {}
		# Compute the maximum theoretically possible throughput
		sending_units = sum([chiplets[x["name"]]["unit_count"] for x in placement["chiplets"] if (chiplets[x["name"]]["type"][0].upper() == traffic[0])])
		# Compute throughputs of all paths in this class
		path_throughputs = []
		for (src,dst) in paths_per_class[traffic]:
			path = paths_per_class[traffic][(src,dst)]
			path_throughputs.append(1.0 / max([n_paths_per_edge_per_class[traffic][(path[i], path[i+1])] for i in range(len(path)-1)]))
		# Use the most congested path as proxy to estimate congestion
		n_paths = len(path_throughputs)
		path_throughputs_sorted = sorted(path_throughputs)
		tp = min((n_paths * path_throughputs_sorted[0]) / sending_units, 1.0)
		# Compute and store statistics
		ici_throughputs[traffic]["fraction_of_theoretical_peak"] = tp
		ici_throughputs[traffic]["all_per_path_throughputs"] = path_throughputs
	# Return results
	return ici_throughputs
		
# Perform the thermal analysis
def compute_thermal_analysis(chiplets, placement, packaging, thermal_config, area_summary):	
	# Compute grid-size
	resolution	= thermal_config["resolution"]
	rows = int(math.ceil(area_summary["chip_height"] / resolution))
	cols = int(math.ceil(area_summary["chip_width"] / resolution))
	(cell_width, cell_height) = (area_summary["chip_width"] / cols, area_summary["chip_height"] / rows)
	# For each grid-cell, compute the temperature increase due to incoming energy from chiplets / irouters
	temperature_in = [[0 for i in range(cols)] for j in range(rows)]
	k_c = thermal_config["k_c"]
	k_i = thermal_config["k_i"]
	# Compute incoming power due to chiplets	
	for chiplet_desc in placement["chiplets"]:
		chiplet = chiplets[chiplet_desc["name"]]
		(x,y) = (chiplet_desc["position"]["x"],chiplet_desc["position"]["y"])
		(w,h) = (chiplet["dimensions"]["x"],chiplet["dimensions"]["y"])
		chiplet_pwr = chiplet["power"]
		pwr_per_mm2 = chiplet_pwr / (w *h)
		temp_per_mm2 = pwr_per_mm2 * k_c
		row = int(math.floor(y / cell_height))
		while row <= (((y + h) / cell_height) - 1) and row < rows:
			col = int(math.floor(x / cell_width))
			while col <= (((x + w) / cell_width) - 1) and col < cols:
				temperature_in[row][col] += temp_per_mm2
				col += 1
			row +=1 
	# Compute incoming power due to interposer_routers
	# TODO: For now, we simply add the energy to a single cell. For high resolutions, this can produce hotspots.
	irouter_pwr = (packaging["power_irouter"] if "power_irouter" in packaging else 0)
	for irouter in placement["interposer_routers"]:
		(x,y) = (irouter["position"]["x"],irouter["position"]["y"])
		row = int(math.floor(y / cell_height))
		col = int(math.floor(x / cell_width))
		temperature_in[row][col] += (irouter_pwr * k_i)
	# Perform simulation
	amb = thermal_config["ambient_temperature"]
	k_t = thermal_config["k_t"]
	k_s = thermal_config["k_s"]
	k_hs = thermal_config["k_hs"]
	temperature = [[amb for i in range(cols)] for j in range(rows)]
	iter_count = 0
	diff = float("inf")
	while iter_count < thermal_config["iteration_limit"] and diff > thermal_config["threshold"]:
		iter_count += 1
		temperature_new = copy.deepcopy(temperature)	
		# Update all grid cells
		for row in range(rows):
			for col in range(cols):
				# Apply incoming energy form chiplets / irouters 
				temperature_new[row][col] += temperature_in[row][col]
				# Apply horizontal heat transfer
				from_left = 0 if col == 0 else (temperature[row][col-1] - temperature[row][col])
				from_right = 0 if col == (cols - 1) else (temperature[row][col+1] - temperature[row][col])
				from_bottom = 0 if row == 0 else (temperature[row-1][col] - temperature[row][col])
				from_top = 0 if row == (rows - 1) else (temperature[row+1][col] - temperature[row][col])
				temperature_new[row][col] += k_t * (from_left + from_right + from_bottom + from_top)
				# Apply outgoing energy through heat sink 
				temperature_new[row][col] -= (k_hs * abs(temperature[row][col] - amb))
		# Apply heat dissipated through the side of the chip
		for row in range(rows):	
			temperature_new[row][0] -= (k_s * abs(temperature[row][0] - amb))
			temperature_new[row][cols-1] -= (k_s * abs(temperature[row][cols-1] - amb))
		for col in range(cols):	
			temperature_new[0][col] -= (k_s * abs(temperature[0][col] - amb))
			temperature_new[rows-1][col] -= (k_s * abs(temperature[rows-1][col] - amb))
		# Compute the total change in temperature 
		diff_sum = sum([abs(temperature[row][col] - temperature_new[row][col]) for row in range(rows) for col in range(cols)])
		diff = diff_sum / (rows * cols)
		# Update grid
		temperature = temperature_new
	temperature_flat = [x for inner in temperature for x in inner]
	thermal_analysis = {
		"avg" : sum(temperature_flat) / len(temperature_flat),
		"min" : min(temperature_flat),
		"max" : max(temperature_flat),
		"grid" : temperature,
		"iterations_simulated" : iter_count
	}
	return thermal_analysis 
		
# Compute the selected metrics
def compute_metrics(design, results_file, compute_area, compute_power, compute_link, compute_cost, compute_latency, compute_throughput, compute_thermal, routing):
	# Results
	results = {}
	# Timing
	timing = {}
	start_time_overall = time.time()	
	start_time = time.time()	
	# Update flags for metrics that are internally used for other metrics
	compute_ici_graph = compute_latency or compute_throughput
	compute_area = compute_area or compute_cost or compute_thermal
	compute_link = compute_link or compute_latency
	# Technology node
	technology = None
	if compute_cost or compute_latency:	
		technology = hlp.read_file(filename = design["technology_nodes_file"])
	# Chiplets 
	chiplets = None
	if compute_area or compute_power or compute_link or compute_cost or compute_ici_graph or compute_latency or compute_throughput or compute_thermal:	
		chiplets = hlp.read_file(filename = design["chiplets_file"])
	# Placement
	placement = None
	if compute_area or compute_power or compute_link or compute_cost or compute_ici_graph or compute_latency or compute_throughput or compute_thermal:	
		placement = hlp.read_file(filename = design["chiplet_placement_file"])
	# Topology
	topology = None
	if compute_link or compute_ici_graph:	
		topology = hlp.read_file(filename = design["ici_topology_file"])
	# Packaging
	packaging = None
	if compute_power or compute_link or compute_cost or compute_latency or compute_thermal:	
		packaging = hlp.read_file(filename = design["packaging_file"])
	# Temperature Config 
	thermal_config = None
	if compute_thermal:
		thermal_config = hlp.read_file(filename = design["thermal_config"])
	# Update timing stats
	timing["reading_inputs"] = time.time() - start_time
	start_time = time.time()
	# Validate design
	if not vld.validate_design(design, technology, chiplets, placement, topology, packaging, thermal_config):
		print("warning: This design contains validation errors - the RapidChiplet toolchain might fail.")
	# Update timing stats
	timing["validating"] = time.time() - start_time
	start_time = time.time()
	# Only construct the ICI graph if we need it (i.e. if latency or throughput are computed)
	if compute_ici_graph:
		ici_graph = construct_ici_graph(chiplets, placement, topology)
		if not vld.validate_ici_graph(ici_graph):
			print("warning: The ICI topology contains validation errors - the RapidChiplet toolchain might fail.")
		ici_routing = construct_ici_routing(ici_graph, routing)
	# Update timing stats
	timing["processing_inputs"] = time.time() - start_time
	start_time = time.time()
	# Compute the area summary
	if compute_area:
		area_summary = compute_area_summary(chiplets, placement)
		results["area_summary"] = area_summary 
		# Update timing stats
		timing["computing_area_summary"] = time.time() - start_time
		start_time = time.time()
	# Compute the power summary
	if compute_power:
		power_summary = compute_power_summary(chiplets, placement, packaging)
		results["power_summary"] = power_summary 
		# Update timing stats
		timing["computing_power_summary"] = time.time() - start_time
		start_time = time.time()
	# Compute the link summary
	link_lengths_internal = None
	if compute_link:
		(link_summary, link_lengths_internal) = compute_link_summary(chiplets, placement, topology, packaging)
		results["link_summary"] = link_summary 
		# Update timing stats
		timing["computing_link_summary"] = time.time() - start_time
		start_time = time.time()
	# Compute the manufacturing cost
	if compute_cost:
		manufacturing_cost = compute_manufacturing_cost(technology, chiplets, placement, packaging, area_summary)
		results["manufacturing_cost"] = manufacturing_cost 
		# Update timing stats
		timing["computing_manufacturing_cost"] = time.time() - start_time
		start_time = time.time()
	# Compute ICI latency
	if compute_latency:
		ici_latency = compute_ici_latency(technology, chiplets, placement, packaging, ici_graph, ici_routing, link_lengths_internal)
		results["ici_latency"] = ici_latency 
		# Update timing stats
		timing["computing_ici_latency"] = time.time() - start_time
		start_time = time.time()
	# Compute ICI throughput
	if compute_throughput:
		ici_throughput = compute_ici_throughput(chiplets, placement, ici_graph, ici_routing)
		results["ici_throughput"] = ici_throughput
		# Update timing stats
		timing["computing_ici_throughput"] = time.time() - start_time
		start_time = time.time()
	# Thermal analysis
	if compute_thermal:
		thermal_analysis = compute_thermal_analysis(chiplets, placement, packaging, thermal_config, area_summary)
		results["thermal_analysis"] = thermal_analysis 
		# Update timing stats
		timing["thermal_analysis"] = time.time() - start_time
		start_time = time.time()
	# Update timing stats
	timing["total_runtime"] = time.time() - start_time_overall
	# Add timing to results
	results["runtime"] = timing
	# Store results
	hlp.write_file("./results/%s.json" % results_file, results)

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()	
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file") 
	parser.add_argument("-rf", "--results_file", required = True, help = "Name of the results file (is stored in ./results/)")
	parser.add_argument("-r", "--routing", required = False, help = "Use the non-default \"balanced\" or \"random\" routing")
	parser.add_argument("-as", "--area_summary", action="store_true", help = "Compute the area summary")
	parser.add_argument("-ps", "--power_summary", action="store_true", help = "Compute the power summary")
	parser.add_argument("-ls", "--link_summary", action="store_true", help = "Compute the link summary")
	parser.add_argument("-c", "--cost", action="store_true", help = "Compute the manufacturing cost")
	parser.add_argument("-T", "--thermal", action="store_true", help = "Compute the thermal analysis")
	parser.add_argument("-l", "--latency", action="store_true", help = "Compute the ICI latency")
	parser.add_argument("-t", "--throughput", action="store_true", help = "Compute the ICI throughput")
	args = parser.parse_args()
	# Read the design file
	design = hlp.read_file(filename = args.design_file)
	# Compute metrics
	compute_metrics(design = design, 
					results_file = args.results_file, 
					compute_area = args.area_summary,
					compute_power = args.power_summary,
					compute_link = args.link_summary,
					compute_cost = args.cost, 
					compute_latency = args.latency,
					compute_throughput = args.throughput,
					compute_thermal = args.thermal,
					routing = args.routing)

