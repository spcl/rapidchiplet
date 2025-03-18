# Import python libraries
import networkx as nx
import itertools as it
from copy import deepcopy

#modifies the parameter graph, returns a cycle breaking set of turns for G
def simple_cycle_breaking(G, forbidden_turns):
    #end of recursion
    if G.number_of_nodes() == 2:
        return
    else:
        #compute all cut nodes:
        cut_vertices = (list(nx.articulation_points(G)))
        #compute a min deg non cut vertice 
        min_deg = min([G.degree(x) for x in list(G.nodes()) if x not in cut_vertices])
        non_cut_min_vertices = [x for x in list(G.nodes()) if x not in cut_vertices and G.degree(x) == min_deg]
        
        #find vertex for step 2 in algo
        chosen_vertex = -1
        for x in non_cut_min_vertices:
            #check if ineq from paper
            if G.degree(x) <= sum([G.degree(v)-1 for v in G[x]]):
                chosen_vertex = x
                break
        assert(chosen_vertex != -1)
        #add forbidden turns to forbidden turn list
        for neigh1,neigh2 in it.combinations(G[chosen_vertex],2):
            forbidden_turns.append(((neigh1,chosen_vertex), (chosen_vertex, neigh2)))
            forbidden_turns.append(((neigh2,chosen_vertex), (chosen_vertex, neigh1)))

        G.remove_node(chosen_vertex)
        simple_cycle_breaking(G, forbidden_turns)

# corresponds one to one to the cpp booksim code.
def generate_line_graph(G: nx.DiGraph):
    LG = nx.DiGraph()
    for e in G.edges():
        LG.add_node(e)

    for v1 in G.nodes():
        for v2 in G.nodes():
            for v3 in G.nodes():
                if v1 != v3 and (v1,v2) in G.edges() and (v2,v3) in G.edges():
                    LG.add_edge((v1,v2),(v2,v3))

    return LG

# computes the predecessor map for all paths starting from chiplets. nx.predecessor computes the predecessor map containing all possible predecesssors on
# shortest paths from src to other nodes. note that this is called on the dual graph and thus the starting point in the algo corresponds to an edge in the original graph.
def get_shortest_valid_paths(LG, chiplets, src, pred_map):
    #now compute minimal paths for each pair of nodes in the graph. first iterate over all pairs of nodes:
    for u in chiplets:
        pred_map[u] = deepcopy(nx.predecessor(LG,(src,u)))
        
            
    
