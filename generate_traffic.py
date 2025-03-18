# Import python libraries
import sys
import math
import copy
import random
import argparse

# Import RapidChiplet files
import helpers as hlp

# Generate random uniform traffic
# Inputs:
# sending_types: list of chiplet-types that send traffic (e.g. compute, memory, io)
# receiving_types: list of chiplet-types that receive traffic (e.g. compute, memory, io)
# Outputs:
# traffic: dictionary with source-chiplet-id and destination-chiplet-id as keys and 
# 		   average number of packets per cycle as values
def generate_random_uniform_traffic(placement, chiplets, sending_types, receiving_types):
	# Identify chiplets that send and receive traffic
	source_cids = [cid for (cid, cdesc) in enumerate(placement["chiplets"]) if chiplets[cdesc["name"]]["type"] in sending_types] 
	destination_cids= [cid for (cid, cdesc) in enumerate(placement["chiplets"]) if chiplets[cdesc["name"]]["type"] in receiving_types]
	# Generate random uniform traffic
	traffic = {}
	for src_cid in source_cids:
		src_chiplet = chiplets[placement["chiplets"][src_cid]["name"]]	
		for src_uid in range(src_chiplet["unit_count"]):
			src = (src_cid, src_uid)	
			active_destination_cids = [cid for cid in destination_cids if cid != src_cid]	
			n_dst = sum([chiplets[placement["chiplets"][cid]["name"]]["unit_count"] for cid in active_destination_cids])
			for dst_cid in active_destination_cids:
				dst_chiplet = chiplets[placement["chiplets"][dst_cid]["name"]]
				for dst_uid in range(dst_chiplet["unit_count"]):
					dst = (dst_cid, dst_uid)
					traffic[(src, dst)] = 1.0 / n_dst
	return traffic

# Generate transpose traffic
# This function assumes a square placement of chiplets
def generate_transpose_traffic(placement, chiplets):
	# Identify chiplets that send and receive traffic
	cids = [cid for (cid, cdesc) in enumerate(placement["chiplets"])] 
	if math.sqrt(len(cids)) % 1.0 != 0:
		print("ERROR: Permutation traffic pattern only works with square placements")
		sys.exit(1)
	n_rows = int(math.sqrt(len(cids)))
	n_cols = int(math.sqrt(len(cids)))
	# Generate random uniform traffic
	traffic = {}
	for src_cid in cids:
		(src_row, src_col) = (src_cid // n_cols, src_cid % n_cols)
		src_chiplet = chiplets[placement["chiplets"][src_cid]["name"]]	
		for src_uid in range(src_chiplet["unit_count"]):
			src = (src_cid, src_uid)	
			dst_cid = src_col * n_cols + src_row
			# Nodes on the diagonal do not send traffic to themselves
			if dst_cid != src_cid:
				dst_chiplet = chiplets[placement["chiplets"][dst_cid]["name"]]
				n_dst = dst_chiplet["unit_count"]
				for dst_uid in range(dst_chiplet["unit_count"]):
					dst = (dst_cid, dst_uid)
					traffic[(src, dst)] = 1.0 / n_dst
	return traffic

# Generate permutation traffic
def generate_permutation_traffic(placement, chiplets):
	# Identify chiplets that send and receive traffic
	cids = [cid for (cid, cdesc) in enumerate(placement["chiplets"])] 
	# Select a random permutation
	perm = copy.deepcopy(cids)
	while len([src_cid for (src_cid, dst_cid) in enumerate(perm) if src_cid == dst_cid]) > 0:
		random.shuffle(perm)
	# Generate random uniform traffic
	traffic = {}
	for src_cid in cids:
		src_chiplet = chiplets[placement["chiplets"][src_cid]["name"]]	
		for src_uid in range(src_chiplet["unit_count"]):
			src = (src_cid, src_uid)	
			dst_cid = perm[src_cid]
			dst_chiplet = chiplets[placement["chiplets"][dst_cid]["name"]]
			n_dst = dst_chiplet["unit_count"]
			for dst_uid in range(dst_chiplet["unit_count"]):
				dst = (dst_cid, dst_uid)
				traffic[(src, dst)] = 1.0 / n_dst
	return traffic

# Generate hotspot traffic
def generate_hotspot_traffic(placement, chiplets, n_hotspots, p_hotspots):
	# Identify chiplets that send and receive traffic
	source_cids = [cid for (cid, cdesc) in enumerate(placement["chiplets"])] 
	# Randomly select hotspots
	hotspots = random.sample(source_cids, n_hotspots)
	non_hotspots = [cid for cid in source_cids if cid not in hotspots]
	# Generate hotspot traffic
	traffic = {}
	for src_cid in source_cids:
		src_chiplet = chiplets[placement["chiplets"][src_cid]["name"]]	
		for src_uid in range(src_chiplet["unit_count"]):
			src = (src_cid, src_uid)	
			unused_load = 0.0
			for (destination_cids, agg_load) in [(hotspots, p_hotspots), (non_hotspots, 1.0 - p_hotspots)]:
				agg_load += unused_load
				active_destination_cids = [cid for cid in destination_cids if cid != src_cid]
				if len(active_destination_cids) > 0:
					n_dst = sum([chiplets[placement["chiplets"][cid]["name"]]["unit_count"] for cid in active_destination_cids])
					for dst_cid in active_destination_cids:
						dst_chiplet = chiplets[placement["chiplets"][dst_cid]["name"]]
						for dst_uid in range(dst_chiplet["unit_count"]):
							dst = (dst_cid, dst_uid)
							traffic[(src, dst)] = agg_load / n_dst
				else:
					unused_load = agg_load
	return traffic

def generate_traffic(chiplets, placement, traffic_pattern, params):
	# Construct traffic
	if traffic_pattern == "random_uniform":
		sending_types = params[0]
		receiving_types = params[1]
		traffic_by_unit = generate_random_uniform_traffic(placement, chiplets, sending_types, receiving_types)
	elif traffic_pattern == "transpose":
		traffic_by_unit = generate_transpose_traffic(placement, chiplets)
	elif traffic_pattern == "permutation":
		traffic_by_unit = generate_permutation_traffic(placement, chiplets)
	elif traffic_pattern == "hotspot":
		n_hotspots = params[0]
		p_hotspots = params[1]
		traffic_by_unit = generate_hotspot_traffic(placement, chiplets, n_hotspots, p_hotspots)
	else:
		print("ERROR: Unknown synthetic traffic pattern: %s" % traffic_pattern)
		sys.exit(1)
	# Convert traffic by unit to traffic by chiplet
	traffic_by_chiplet = hlp.convert_by_unit_traffic_to_by_chiplet_traffic(traffic_by_unit)
	return (traffic_by_unit, traffic_by_chiplet)
		

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file")
	parser.add_argument("-tf", "--traffic_file", required = True, help = "Name of the traffic file (is stored in ./inputs/traffic_by_unit and ./inputs/traffic_by_chiplet)")
	parser.add_argument("-tp", "--traffic_pattern", required = True, help = "Traffic pattern to use. Options: random_uniform")
	parser.add_argument("-par", "--parameters", required = False, help = "Additional parameters for the specified traffic pattern")
	args = parser.parse_args()
	# Read input files
	design = hlp.read_json(filename = args.design_file)
	chiplets = hlp.read_json(filename = design["chiplets"])
	placement = hlp.read_json(filename = design["placement"])
	# Generate synthetic traffic
	parameters = eval(args.parameters) if args.parameters is not None else []
	traffic_file = args.traffic_file
	(traffic_by_unit, traffic_by_chiplet) = generate_traffic(chiplets, placement, args.traffic_pattern, parameters)
	# Store results
	hlp.write_json("./inputs/traffic_by_unit/%s.json" % traffic_file, traffic_by_unit)
	hlp.write_json("./inputs/traffic_by_chiplet/%s.json" % traffic_file, traffic_by_chiplet)


