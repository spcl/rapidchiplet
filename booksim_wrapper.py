# Import python libraries
import math
import copy
import subprocess

# Import RapidChiplet files
import helpers as hlp

# Export the BookSim configuration file
def export_booksim_config(inputs, run_identifier, load):
	# Read required inputs if not already present in inputs
	required_inputs = ["booksim_config","chiplets","packaging","placement","routing_table"]
	hlp.read_required_inputs(inputs, required_inputs)
	booksim_config = inputs["booksim_config"]
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	routing_table_type = inputs["routing_table"]["type"]
	# Prepare the BookSim configuration file for export
	bsc = copy.deepcopy(booksim_config)
	# Remove parameters that are used by RapidChiplet and not by BookSim
	del bsc["precision"]
	del bsc["saturation_factor"]
	# Determine router latency used in BookSim. This can be set manually in the BookSim configuration file
	# If not specified, the average latency of chiplet-internal-routers and interposer-routers is used
	if "router_latency" in bsc:
		router_latency = bsc["router_latency"]
		del bsc["router_latency"]
	else:
		router_latencies = [chiplets[x["name"]]["internal_latency"] for x in placement["chiplets"]]
		router_latencies += [packaging["latency_irouter"] for x in placement["interposer_routers"]]	
		router_latency = int(math.ceil(sum(router_latencies) / len(router_latencies)))
		if len(set(router_latencies)) > 1:	
			print("WARNING: In BookSim simulations, all routers (on-chip or on-interposer) have the same latency. " + \
			  "In your configuration, these latencies are not identical. RapidChiplet will use the average " + \
			  "latency which is %d cycles. To manually set the router-latency, " % router_latency + \
			  "specify the parameter \"router_latency\" in the booksim-config input file.")
	# 1) Simulation parameters
	bsc["topology"] = "anynet" 
	bsc["network_file"] = "booksim2/src/rc_topologies/%s.anynet" % run_identifier
	bsc["routing_table_type"] = routing_table_type
	bsc["routing_table_file"] = "booksim2/src/rc_routing_tables/%s.json" % run_identifier
	bsc["traffic_file"] = "booksim2/src/rc_traffics/%s.json" % run_identifier
	bsc["trace_file"] = "booksim2/src/rc_traces/%s.json" % run_identifier
	bsc["injection_rate"] = 1.0 if bsc["mode"] == "trace" else load
	# 3) Parameters related to the timing/latencies:
	bsc["credit_delay "] = 0
	bsc["routing_delay "] = 0
	bsc["vc_alloc_delay "] = 1
	bsc["sw_alloc_delay "] = 1
	bsc["st_final_delay "] = max(1, router_latency - 2)
	bsc["input_speedup "] = 1
	bsc["output_speedup "] = 1
	bsc["internal_speedup "] = (1.0 if router_latency >= 3 else (3.0 / router_latency))
	# 4) More simulation parameters
	bsc["use_read_write "] = 0
	bsc["routing_function "] = "min"
	bsc["traffic"] = "custom"
	bsc["injection_process"] = "custom"
	# Convert configuration file to correct format
	config_lines = [(key + " = " + str(bsc[key]) + ";") for key in bsc]
	# Store the file
	save_path = "booksim2/src/rc_configs/%s.conf" % run_identifier
	with open(save_path, "w") as file:
		for line in config_lines:
			file.write(line + "\n")


# Write the BookSim topology file
# Router-IDs 0 to c-1 are chiplet-internal routers (with nodes), ids c to c+r-1 are interposer routers (with nodes)
# Node-IDs are consecutive starting units of chiplet 0 to units of chiplet c-1
# Router-latencies are the chiplets internal latency or the interposer-router latency
# Link latencies are the sum of outgoing-phy-latency, link-latency, and incoming-phy-latency
def export_booksim_topology(inputs, intermediates, run_identifier):
	# Read required inputs
	required_inputs = ["chiplets","placement","technologies","topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	technologies = inputs["technologies"]
	topology = inputs["topology"]
	n_chiplets = len(placement["chiplets"])
	# Compute intermediates
	required_intermediates = ["link_latencies"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_latencies = intermediates["link_latencies"]
	# Load or compute additional information 
	ici_graph = hlp.construct_ici_graph(chiplets, placement, topology)
	adj_list = ici_graph["adj_list"]
	# Create the topology input file for BookSim
	topology_lines = []
	# In addition, construct a port map: {(cur_type, cur_id) -> {(next_type, next_id) -> port}}
	# This map is later used to construct the routing table
	port_map = {}
	# Write one line per chiplet (central router -> nodes -> links to other routers)
	running_node_id_counter = 0
	for (cid, chiplet_desc) in enumerate(inputs["placement"]["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		phy_latency = technologies[chiplet["technology"]]["phy_latency"]
		# The chiplets central router
		line = "router % d" % cid
		port_map_entry = {}
		# Add nodes (ports 0 to u-1 for u units)
		for uid in range(chiplet["unit_count"]):
			line += " node %d" % running_node_id_counter
			port_map_entry[("unit",running_node_id_counter)] = uid
			running_node_id_counter += 1
		# Add links to other routers
		for (cnt, (otype, oid)) in enumerate(sorted(adj_list[("chiplet", cid)], key=lambda x: (0 if x[0] == "chiplet" else 1, x[1]))):
			ophy_latency = technologies[chiplet["technology"]]["phy_latency"] if otype == "chiplet" else 0
			bs_oid = oid if otype == "chiplet" else n_chiplets + oid
			lat = phy_latency + link_latencies[(("chiplet",cid),(otype,oid))] + ophy_latency
			line += " router %d %d" % (bs_oid, lat)
			port_map_entry[(otype,oid)] = chiplet["unit_count"] + cnt
		topology_lines.append(line)
		port_map[("chiplet",cid)] = port_map_entry
	# Write one line for each interposer-router
	for rid in range(len(placement["interposer_routers"])):
		bs_rid = n_chiplets + rid
		line = "router %d" % bs_rid
		port_map_entry = {}
		# Add links to other routers
		for (cnt, (otype, oid)) in enumerate(sorted(adj_list[("irouter",rid)], key=lambda x: (0 if x[0] == "chiplet" else 1, x[1]))):
			ophy_latency = technologies[chiplet["technology"]]["phy_latency"] if otype == "chiplet" else 0
			bs_oid = oid if otype == "chiplet" else n_chiplets + oid
			lat = link_latencies[(("irouter",rid),(otype,oid))] + ophy_latency
			line += " router %d %d" % (bs_oid, lat)
			port_map_entry[(otype,oid)] = cnt
		topology_lines.append(line)
		port_map[("irouter",rid)] = port_map_entry
	# Store the file
	save_path = "booksim2/src/rc_topologies/%s.anynet" % run_identifier
	with open(save_path, "w") as file:
		for line in topology_lines:
			file.write(line + "\n")
	# Return the port map
	return port_map


# Export the routing table: Convert from RapidChiplet format to BookSim format
# RapidChiplet routing table format: Uses pairs of type and if for cur, dst, next and prev.
# "default"-mode: {(cur_type, cur_id) -> {(dst_type, dst_id) -> (next_type, next-id)}}
# "extended"-mode: {(cur_type, cur_id) -> {(dst_type, dst_id) -> {(prev_type, prev_id) -> (next_type, next-id)}}}
# BookSim routing table format: Uses router-ids for cur, next, and prev but uses node-ids for dst
# "default"-mode: routing_table[cur_bs_rid] = {dst_bs_nid -> output_port}
# "extended"-mode: routing_table[cur_bs_rid] = {dst_bs_nid -> {input_port -> output_port}}
def export_routing_table(inputs, intermediates, port_map, run_identifier):
	# Read required inputs
	required_inputs = ["chiplets","placement","routing_table"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	routing_table_ = inputs["routing_table"]
	routing_table_type = routing_table_["type"]
	routing_table = routing_table_["table"]
	n_chiplets = len(placement["chiplets"])
	n_irouters = len(placement["interposer_routers"])
	# Units in RapidChiplet correspond to nodes in BookSim. They are the destination of packets in BookSim
	# This map maps unit-ids to the chiplet-id that they are part of
	unit_id_to_chiplet_id = {}
	n_units = 0
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		for uid in range(chiplet["unit_count"]):
			unit_id_to_chiplet_id[n_units] = cid
			n_units += 1
	# Construct the BookSim routing table
	bs_routing_table = []
	# Add all chiplet-routers to the table
	next_local_unit_id = 0
	for cid in range(n_chiplets):
		sub_table = {}
		# Add all units/nodes to the table	
		for uid in range(n_units):
			units_partent_cid = unit_id_to_chiplet_id[uid]
			# If destination is a local unit, directly send traffic to the node, independent of the previous node
			if units_partent_cid == cid:
				# Default: Send packet to port where corresponding unit is attached
				if routing_table_type == "default":
					sub_table[uid] = port_map[("chiplet",cid)][("unit",uid)]
				# Extended: Create s sub-table that, for every possible input-port, sends the packet to the
				# 			output port where the corresponding unit is attached
				else:
					sub_sub_table = {}
					for prev_port in port_map[("chiplet",cid)].values():
						sub_sub_table[prev_port] = port_map[("chiplet",cid)][("unit",uid)]
					sub_table[uid] = sub_sub_table
			# If destination is not a local unit, add a link to the next router on the path to the destination
			else:
				# Default routing table type: Only one next hop
				if routing_table_type == "default":
					(next_type, next_id) = routing_table[("chiplet",cid)][("chiplet",units_partent_cid)]
					sub_table[uid] = port_map[("chiplet",cid)][next_type,next_id]
				# Extended routing table type: Next-hop depends on input port
				elif routing_table_type == "extended":
					sub_sub_table = {}
					# Routing for packets that are injected at the current chiplet
					for local_unit in range(chiplets[placement["chiplets"][cid]["name"]]["unit_count"]):
						prev_port = port_map[("chiplet",cid)][("unit",next_local_unit_id + local_unit)]
						(next_type, next_id) = routing_table[("chiplet",cid)][("chiplet",units_partent_cid)]["-1"]
						sub_sub_table[prev_port] = port_map[("chiplet",cid)][next_type,next_id]
					# Routing for packets that are not injected at the current chiplet
					for prev in routing_table[("chiplet",cid)][("chiplet",units_partent_cid)].keys():
						if prev != "-1":
							prev_port = port_map[("chiplet",cid)][prev]
							(next_type, next_id) = routing_table[("chiplet",cid)][("chiplet",units_partent_cid)][prev]
							sub_sub_table[prev_port] = port_map[("chiplet",cid)][next_type,next_id]
					sub_table[uid] = sub_sub_table
				else:
					print("ERROR: Invalid routing table type \"%s\"" % routing_table_type)
					sys.exit(1)
		next_local_unit_id += chiplets[placement["chiplets"][cid]["name"]]["unit_count"]
		# Order in the table specifies the router to which this sub-table belongs
		bs_routing_table.append(sub_table)
	# Add all interposer-routers to the table
	for rid in range(n_irouters):
		sub_table = {}
		# Add all units/nodes to the table
		for	uid in range(n_units):
			# Default routing table type: Only one next hop
			if routing_table_type == "default":
				(next_type, next_id) = routing_table[("irouter",rid)][("chiplet",unit_id_to_chiplet_id[uid])]
				sub_table[uid] = port_map[("irouter",rid)][next_type,next_id]
			# Extended routing table type: Next-hop depends on input port
			elif routing_table_type == "extended":
				sub_sub_table = {}
				for (prev_type, prev_id) in port_map[("irouter",rid)].keys():
					prev_port = port_map[("irouter",rid)][(prev_type,prev_id)]
					(next_type, next_id) = routing_table[("irouter",rid)][("chiplet",unit_id_to_chiplet_id[uid])][(prev_type,prev_id)]
					sub_sub_table[prev_port] = port_map[("irouter",rid)][next_type,next_id]
				sub_table[uid] = sub_sub_table
			else:
				print("ERROR: Invalid routing table type \"%s\"" % routing_table_type)
				sys.exit(1)
		# Order in the table specified the router to which this sub-table belongs
		bs_routing_table.append(sub_table)
	# Store the file
	save_path = "booksim2/src/rc_routing_tables/%s.json" % run_identifier
	hlp.write_json(save_path, bs_routing_table)

# Export the traffic file for BookSim
def export_traffic(inputs, intermediates, run_identifier):
	# Read required inputs
	required_inputs = ["chiplets","placement","traffic_by_unit"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	traffic_by_unit = inputs["traffic_by_unit"]
	# Construct a map that maps (chiplet-id, unit-id)-pairs to the corresponding BookSim node-id
	cid_and_uid_to_bsnid = {}
	n_nodes = 0
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		for uid in range(chiplet["unit_count"]):
			cid_and_uid_to_bsnid[(cid,uid)] = n_nodes 
			n_nodes += 1
	# Construct the traffic file for BookSim
	# Index corresponds to the sending chiplet/router
	bs_traffic = [[0.0 for i in range(n_nodes)] for i in range(n_nodes)]
	for ((scid,suid),(dcid,duid)) in traffic_by_unit.keys():
		bs_snid = cid_and_uid_to_bsnid[(scid,suid)]
		bs_dnid = cid_and_uid_to_bsnid[(dcid,duid)]
		bs_traffic[bs_snid][bs_dnid] = traffic_by_unit[(scid,suid),(dcid,duid)]
	# Store the file
	save_path = "booksim2/src/rc_traffics/%s.json" % run_identifier
	hlp.write_json(save_path, bs_traffic)

# Export the trace file for BookSim
def export_trace(inputs, intermediates, run_identifier):
	# Read required inputs
	required_inputs = ["chiplets","placement","trace"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	trace = inputs["trace"]
	# Construct a map that maps (chiplet-id, unit-id)-pairs to the corresponding BookSim node-id
	cid_and_uid_to_bsnid = {}
	n_nodes = 0
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		for uid in range(chiplet["unit_count"]):
			cid_and_uid_to_bsnid[(cid,uid)] = n_nodes 
			n_nodes += 1
	# Construct the trace file for BookSim
	bs_trace = []
	num_deps = {packet["id"] : 0 for packet in trace}
	for packet in trace:	
		bs_packet = {}
		bs_packet["id"] = packet["id"]
		bs_packet["cycle"] = packet["injection_cycle"]
		bs_packet["src"] = cid_and_uid_to_bsnid[(packet["source_chiplet"],packet["source_unit"])]
		bs_packet["dst"] = cid_and_uid_to_bsnid[(packet["destination_chiplet"],packet["destination_unit"])]
		bs_packet["rev_deps"] = packet["reverse_dependencies"]
		bs_packet["num_flits"] = packet["size_in_flits"]
		for rev_dep in packet["reverse_dependencies"]:
			num_deps[rev_dep] += 1
		bs_trace.append(bs_packet)
	# Add the number of dependencies per packet
	for packet in bs_trace:
		packet["num_deps"] = num_deps[packet["id"]]
	# Store the file
	save_path = "booksim2/src/rc_traces/%s.json" % run_identifier
	hlp.write_json(save_path, bs_trace)

# Print BookSim errors
def print_booksim_error_if_applicable(out, err):
	out_string = out.decode("utf-8")
	err_string = err.decode("utf-8")
	if len(err_string) > 0:
		print("Error during BookSim simulation:")
		print(err_string)
		return True
	return False

# Read the BookSim results
def read_booksim_results(out):
	out_string = out.decode("utf-8")
	result_lines = out_string.split("\n")[-35:]
	metrics = ["Packet latency","Network latency","Flit latency","Fragmentation","Injected packet rate","Accepted packet rate","Injected flit rate","Accepted flit rate"]
	results = {}
	for (line_idx, line) in enumerate(result_lines):
		for metric in metrics:
			if (metric + " average") in line:
				key = metric.lower().replace(" ","_")
				key_length = len(key.split("_"))	
				results[key] = {}
				results[key]["avg"] = float(result_lines[line_idx].split(" ")[key_length + 2]) if len(result_lines[line_idx].split(" ")) > key_length + 2 else float("nan")
				results[key]["min"] = float(result_lines[line_idx+1].split(" ")[2]) if len(result_lines[line_idx+1].split(" ")) > 2 else float("nan")
				results[key]["max"] = float(result_lines[line_idx+2].split(" ")[2])	if len(result_lines[line_idx+2].split(" ")) > 2 else float("nan")
		if "Injected packet size average" in line:
			results["injected_packet_size"] = {}
			results["injected_packet_size"]["avg"] = float(line.split(" ")[5])
		if "Accepted packet size average" in line:
			results["accepted_packet_size"] = {}
			results["accepted_packet_size"]["avg"] = float(line.split(" ")[5])
		if "Hops average" in line:
			results["hops"] = {}
			results["hops"]["avg"] = float(line.split(" ")[3])
		if "Total run time" in line:
			results["total_run_time"] = float(line.split(" ")[3])
		if "Total cycles until trace completion" in line:
			results["total_run_time_cycles"] = float(line.split(" ")[6])
	return results

# Run a BookSim simulation:
# This runs the C++ code which needs to be built manually by executing "make" in the "booksim2/src" directory
def run_booksim_simulation(inputs, intermediates, run_identifier):
	# Load inputs 
	required_inputs = ["booksim_config"]
	hlp.read_required_inputs(inputs, required_inputs)
	booksim_config = inputs["booksim_config"]
	# Configuration
	mode = booksim_config["mode"]
	precision = booksim_config["precision"]
	saturation_factor = booksim_config["saturation_factor"]
	# Paths
	exec_path = "booksim2/src/booksim"
	config_path = "booksim2/src/rc_configs/%s.conf" % run_identifier
	# Prepare the results
	results = {}
	# Traffic mode: Iterate through loads
	if mode == "traffic":
		load = 0.001
		granularity = 0.1
		while True:
			print("Running BookSim simulation with load %.3f" % load) if inputs["verbose"] else None
			saturation_reached = False
			# Export the BookSim configuration file
			export_booksim_config(inputs, run_identifier, load)
			# Run BookSim
			proc = subprocess.Popen([exec_path, config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			out = proc.stdout.read()
			err = proc.stderr.read()
			if print_booksim_error_if_applicable(out, err):
				break
			# If unstable -> Saturation point has been reached
			if "unstable" in out.decode("utf-8"):
				saturation_reached = True
			# If stable -> Read results
			else:
				# Read result
				results[load] = read_booksim_results(out)
				# Check if the run failed
				if "packet_latency" not in results[load]:
					print("Failed run with load %.3f" % load)
					break
				# Check if saturation throughput has been reached
				elif (0.001 in results) and ((results[0.001]["packet_latency"]["avg"] * saturation_factor) < results[load]["packet_latency"]["avg"]):
					saturation_reached = True
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
		results = dict(sorted(results.items()))
	elif mode == "trace":
		print("Running BookSim simulation with trace") if inputs["verbose"] else None
		# Export the BookSim configuration file
		export_booksim_config(inputs, run_identifier, 1.0)
		# Run BookSim
		proc = subprocess.Popen([exec_path, config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out = proc.stdout.read()
		err = proc.stderr.read()
		print_booksim_error_if_applicable(out, err)
		results = read_booksim_results(out)
	else:
		print("ERROR: Invalid mode \"%s\" in BookSim configuration" % mode)
	# Get the number of nodes in the topology
	bs_topo_path = "booksim2/src/rc_topologies/%s.anynet" % run_identifier
	n_nodes = 0
	with open(bs_topo_path, "r") as file:
		lines = file.readlines()
		for line in lines:
			n_nodes += line.count("node")
	results["n_nodes"] = n_nodes
	return results	
