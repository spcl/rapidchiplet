# Import python libraries
import sys
import math
import copy
import argparse
import subprocess

# Import RapidChiplet files
import helpers as hlp
import validation as vld
import rapid_chiplet as rc

def check_units_for_trace_simulations(placement, chiplets):
	# Compute the number of units per chiplet-type
	unit_counts = {"compute" : 0, "memory" : 0, "io" : 0}
	for chiplet_desc in placement["chiplets"]:
		chiplet = chiplets[chiplet_desc["name"]]
		unit_counts[chiplet["type"]] += chiplet["unit_count"]
	# Check that unit-count is below threshold
	valid = True
	for typ in unit_counts:
		if unit_counts[typ] > 64:
			print("error: BookSim simulations with traffic traces only support up to 64 %s-chiplets. " % typ + \
				  "Your design contains %s %s-chiplet" % (unit_counts[typ], typ))
			valid = False
		return valid

def write_topology_anynet(technology, chiplets, placement, topology, packaging, ici_graph, link_lengths_internal, path):
	(c, r, n, neighbors, relay_map, nodes_by_type) = ici_graph
	# Construct the topology.anynet file that BookSim takes as an input
	# We first need to list all compute-chiplets, then all memory-chiplets and then all IO-chiplets
	# and ids need to be consecutive, i.e. we need to remap chiplet ids.
	cid_map = {}
	for typ in ["compute","memory","io"]:
		for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
			if chiplets[chiplet_desc["name"]]["type"] == typ:
				cid_map[cid] = len(cid_map)
	# Add chiplets: One central routers plus one node for each unit (core, memory-bank, memory-controller)
	anynet_lines = []
	next_node_id = 0
	# Again, first list compute-chiplets, then memory, then IO
	for typ in ["compute","memory","io"]:
		for (cid1, chiplet_desc) in enumerate(placement["chiplets"]):
			chiplet = chiplets[chiplet_desc["name"]]
			if chiplet["type"] == typ:
				units = chiplet["unit_count"]
				# 1) list nodes with consecutive ids
				bs_links = [("node %d" % (next_node_id + i)) for i in range(units)]
				next_node_id += units
				# 2) list other chiplets
				for cid2 in [x for x in neighbors[cid1] if x < c]:
					link_lat = packaging["link_latency"] if packaging["link_latency_type"] == "constant" else int(math.ceil(eval(packaging["link_latency"])(link_lengths_internal[(cid1,cid2)])))
					lat = 2 * technology[chiplet["technology"]]["phy_latency"] + link_lat
					bs_links.append(("router %d %d" % (cid_map[cid2], lat)))
				# 3) list interposer-routers	
				for rid in [x for x in neighbors[cid1] if x >= c]:
					link_lat = packaging["link_latency"] if packaging["link_latency_type"] == "constant" else int(math.ceil(eval(packaging["link_latency"])(link_lengths_internal[(cid1,rid)])))
					lat = technology[chiplet["technology"]]["phy_latency"] + link_lat
					bs_links.append(("router %d %d" % (rid, lat)))
				# Add the corresponding line to the anynet-file.
				anynet_lines.append(("router %d " % cid_map[cid1]) + " ".join(bs_links))
	# Add interposer-routers: Keep order as in the input file
	for rid1 in range(c, n):
		bs_links = []
		# 1) list other chiplets
		for cid in [x for x in neighbors[rid1] if x < c]:
			link_lat = packaging["link_latency"] if packaging["link_latency_type"] == "constant" else int(math.ceil(eval(packaging["link_latency"])(link_lengths_internal[(rid1,cid)])))
			lat = technology[chiplet["technology"]]["phy_latency"] + link_lat
			bs_links.append(("router %d %d" % (cid_map[cid], lat)))
		# 3) list interposer-routers	
		# The link traverses no PHY and it has once cycle latency itself
		for rid2 in [x for x in neighbors[rid1] if x >= c]:
			link_lat = packaging["link_latency"] if packaging["link_latency_type"] == "constant" else int(math.ceil(eval(packaging["link_latency"])(link_lengths_internal[(rid1,rid2)])))
			lat = link_lat
			bs_links.append(("router %d %d" % (rid2, lat)))
		# Add the corresponding line to the anynet-file.
		anynet_lines.append(("router %d " % rid1) + " ".join(bs_links))
	# Store the file
	with open(path, "w") as file:
		for line in anynet_lines:
			file.write(line + "\n")

def write_booksim_config(chiplets, placement, booksim_config, topology_path, load, path):
	# Determine router latency for BookSim 
	if "router_latency" in booksim_config:
		router_latency = booksim_config["router_latency"]
	else:
		relay_latencies = [chiplets[x["name"]]["internal_latency"] for x in placement["chiplets"]]
		phy_latencies = [technology[chiplets[x["name"]]["technology"]]["phy_latency"] for x in placement["chiplets"]]
		irouter_latency = (packaging["latency_irouter"] if packaging["is_active"] else 0)
		all_router_latencies = relay_latencies + ([irouter_latency] * len(placement["interposer_routers"]))
		if len(set(all_router_latencies)) > 1:
			router_latency = int(round(sum(all_router_latencies) / len(all_router_latencies)))
			print("warning: In BookSim simulations, all routers (on-chip or on-interposer) have the same latency. " + \
				  "In your configuration, these latencies are not identical. RapidChiplet will use the average " + \
				  "latency which is %d cycles. To manually set the router-latency, " % router_latency + \
				  "specify the parameter \"router_latency\" in the booksim-config input file.")
		else:
			router_latency = all_router_latencies[0]
	# Decide whether all chiplets of a given type can relay traffic or not
	can_relay = {}
	for typ in ["compute","memory","io"]:
		relay_values = [chiplets[x["name"]]["relay"] for x in placement["chiplets"] if chiplets[x["name"]]["type"] == typ]
		if len(set(relay_values)) > 1:
			print("warning: In BookSim simulations, all chiplets of a given type (compute, memory, or io) " + \
				  "have the same relay behaviour, i.e., either all of them can relay traffic or none of them can. " + \
				  "In your configuration, some %s-chiplets can relay traffic and some cannot. " % typ + \
				  "RapidChiplet will set the relay capability to True for all %s-chiplets" % typ)
			can_relay[typ] = True
		else:
			can_relay[typ] = relay_values[0]
		
	# Take the booksim config file for RapidChiplet as basis of the one for BookSim2
	booksim_config_file = copy.deepcopy(booksim_config)
	# Extract parameters needed in this function
	traffic_mode = booksim_config["traffic_mode"]
	trace_mode = booksim_config["trace_mode"]
	traffic = booksim_config["traffic"]
	# Remove parameters that were intended for RapidChiplet and not for BookSim2
	if "router_latency" in booksim_config_file:
		del booksim_config_file["router_latency"]
	if "traffic_mode" in booksim_config_file:
		del booksim_config_file["traffic_mode"]
	if "trace_mode" in booksim_config_file:
		del booksim_config_file["trace_mode"]
	if "precision" in booksim_config_file:
		del booksim_config_file["precision"]
	if "saturation_factor" in booksim_config_file:
		del booksim_config_file["saturation_factor"]
	# Only keep the trace line if the traffic mode is set to trace
	if "trace" in booksim_config_file and traffic_mode != "trace":
		del booksim_config_file["trace"]

	# Add parameters for BookSim2 that were not in the RapidChiplet booksim config file
	# 1) Simulation parameters
	booksim_config_file["topology"] = "anynet" 
	booksim_config_file["network_file"] = topology_path
	booksim_config_file["injection_rate"] = (1.0 if traffic_mode == "trace" else load)
	booksim_config_file["netrace_cycles"] = (0 if trace_mode == "idealized" else 1)
	booksim_config_file["injection_process"] = ("custom" if traffic in ["C2C","C2M","C2I","M2I"] else "bernoulli")
	# 2) Parameters that we added to BookSim for integration into RapidChiplet: Differentiate between chiplet types
	booksim_config_file["n_comp"] = len([x for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "compute"])
	booksim_config_file["n_mem"] = len([x for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "memory"])
	booksim_config_file["n_io"] = len([x for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "io"])
	booksim_config_file["n_comp_units"] = sum([chiplets[x["name"]]["unit_count"] for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "compute"])
	booksim_config_file["n_mem_units"] = sum([chiplets[x["name"]]["unit_count"] for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "memory"])
	booksim_config_file["n_io_units"] = sum([chiplets[x["name"]]["unit_count"] for x in placement["chiplets"] if chiplets[x["name"]]["type"] == "io"])
	booksim_config_file["r_comp"] = 1 if can_relay["compute"] else 0
	booksim_config_file["r_mem"] = 1 if can_relay["memory"] else 0
	booksim_config_file["r_io"] = 1 if can_relay["io"] else 0
	# 3) Parameters related to the timing/latencies:
	booksim_config_file["credit_delay "] = 0
	booksim_config_file["routing_delay "] = 0
	booksim_config_file["vc_alloc_delay "] = 1
	booksim_config_file["sw_alloc_delay "] = 1
	booksim_config_file["st_final_delay "] = max(1, router_latency - 2)
	booksim_config_file["input_speedup "] = 1
	booksim_config_file["output_speedup "] = 1
	booksim_config_file["internal_speedup "] = (1.0 if router_latency >= 3 else (3.0 / router_latency))
	# 4) More simulation parameters
	booksim_config_file["use_read_write "] = 0
	booksim_config_file["latency_thres"] = (str(1000000000000.0) if traffic_mode == "trace" else str(10000.0))
	# Convert config to file format
	config_lines = [(key + " = " + str(booksim_config_file[key]) + ";") for key in booksim_config_file]
	# Store the file
	with open(path, "w") as file:
		for line in config_lines:
			file.write(line + "\n")

def run_booksim_simulation_sub(technology, chiplets, placement, topology, packaging, booksim_config, ici_graph, topology_path, name, precision, saturation_factor, traffic_mode):
	config_path = "booksim2/src/configs/%s.conf" % name 
	# Iterate through loads
	results = {}
	load = (1.0 if traffic_mode == "trace" else 0.001)
	granularity = 0.1
	while True:
		saturation_reached = False
		# Write the BookSim config file
		write_booksim_config(chiplets, placement, booksim_config, topology_path, load, config_path)
		# Run BookSim
		proc = subprocess.Popen(['booksim2/src/booksim', config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out = proc.stdout.read()
		err = proc.stderr.read()
		# BookSim log files
		out_string = out.decode("utf-8")
		err_string = err.decode("utf-8")
		output_log_path = "logs_booksim/output_%s_%.3f.log" % (name, load)
		error_log_path = "logs_booksim/error_%s_%.3f.log" % (name, load)
		with open(output_log_path, "w", encoding = "utf-8") as file:
			file.write(out_string)
		with open(error_log_path, "w", encoding = "utf-8") as file:
			file.write(err_string)
		# If unstable
		if "unstable" in out_string:
			# Saturation point has been reached
			saturation_reached = True
		# If stable: Read results
		else:
			# Read result
			result_lines = out_string.split("\n")[-35:]
			metrics = ["Packet latency","Network latency","Flit latency","Fragmentation","Injected packet rate","Accepted packet rate","Injected flit rate","Accepted flit rate"]
			results[load] = {}
			for (line_idx, line) in enumerate(result_lines):
				for metric in metrics:
					if (metric + " average") in line:
						key = metric.lower().replace(" ","_")
						key_length = len(key.split("_"))	
						results[load][key] = {}
						results[load][key]["avg"] = float(result_lines[line_idx].split(" ")[key_length + 2])
						results[load][key]["min"] = float(result_lines[line_idx+1].split(" ")[2])
						results[load][key]["max"] = float(result_lines[line_idx+2].split(" ")[2])
				if "Injected packet size average" in line:
					results[load]["injected_packet_size"] = {}
					results[load]["injected_packet_size"]["avg"] = float(line.split(" ")[5])
				if "Accepted packet size average" in line:
					results[load]["accepted_packet_size"] = {}
					results[load]["accepted_packet_size"]["avg"] = float(line.split(" ")[5])
				if "Hops average" in line:
					results[load]["hops"] = {}
					results[load]["hops"]["avg"] = float(line.split(" ")[3])
				if "Total run time" in line:
					results[load]["total_run_time"] = float(line.split(" ")[3])
				if "Total time needed in cycles average" in line:
					results[load]["total_run_time_cycles"] = float(line.split(" ")[7])
			# Check if saturation throughput has been reached
			if (0.001 in results) and ((results[0.001]["packet_latency"]["avg"] * saturation_factor) < results[load]["packet_latency"]["avg"]):
				saturation_reached = True
		# If we simulate a trace, we only need one simulation 
		if traffic_mode == "trace":
			break
		# If the saturation point has been reached go to finer granularity or abort
		if saturation_reached:
			# We already are at the maximum precision -> Terminate
			if round(granularity, (-int(math.log(precision)))) <= precision:
				break
			# We can reduce granularity
			else:
				load = (load - granularity) + (granularity / 10)
				granularity *= 0.1
		# Saturation point not reached yet
		elif load < 0.999:
			load = min((0.0 if load == 0.001 else load) + granularity, 0.999)
		# Network can support a load of 0.999 -> Terminate
		else:
			break
	return dict(sorted(results.items()))
			
def run_booksim_simulation(technology, chiplets, placement, topology, packaging, booksim_config, ici_graph, link_lengths_internal, name):
	# Write the topology.anynet file
	topology_path = "booksim2/src/topologies/%s.anynet" % name 
	write_topology_anynet(technology, chiplets, placement, topology, packaging, ici_graph, link_lengths_internal, topology_path)
	# Run simulation for multiple loads
	traffic_mode = booksim_config["traffic_mode"]
	# Check that the design is valid for trace-based simulations
	if booksim_config["traffic_mode"] == "trace" and not check_units_for_trace_simulations(placement, chiplets):
		return None
	# Run for different granularities for synthetic traffic, run only once for real traces
	precision = booksim_config["precision"]
	saturation_factor = booksim_config["saturation_factor"]
	return run_booksim_simulation_sub(technology, chiplets, placement, topology, packaging, booksim_config, ici_graph, topology_path, name, precision, saturation_factor, booksim_config["traffic_mode"])

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()	
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file") 
	parser.add_argument("-rf", "--results_file", required = True, help = "Name of the results file (is stored in ./results/)")
	args = parser.parse_args()
	# Read the design file
	design = hlp.read_file(filename = args.design_file)
	# Read the remaining files
	technology = hlp.read_file(filename = design["technology_nodes_file"])
	chiplets = hlp.read_file(filename = design["chiplets_file"])
	placement = hlp.read_file(filename = design["chiplet_placement_file"])
	topology = hlp.read_file(filename = design["ici_topology_file"])
	packaging = hlp.read_file(filename = design["packaging_file"])
	booksim_config = hlp.read_file(filename = design["booksim_config"])
	# Validate inputs
	vld.validate_design(design, technology, chiplets, placement, topology, packaging, booksim_config = booksim_config)
	# Construct and validate the ICI graph
	ici_graph = rc.construct_ici_graph(chiplets, placement, topology)
	vld.validate_ici_graph(ici_graph)
	# Compute link lengths
	link_lengths_internal = None
	if packaging["link_latency_type"] == "function":
		(link_summary, link_lengths_internal) = rc.compute_link_summary(chiplets, placement, topology, packaging)
	# Run the simulation
	results = run_booksim_simulation(technology, chiplets, placement, topology, packaging, booksim_config, ici_graph, link_lengths_internal, args.results_file)
	# Store results
	result_path = "results/%s.json" % args.results_file
	hlp.write_file(result_path, results)

