# Import python libraries
import sys
import math
import time
import argparse

# Import RapidChiplet files
import helpers as hlp
import booksim_wrapper as bsw

################################################################################################################
# Intermediates
################################################################################################################

def compute_link_lengths(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","packaging","placement","topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	topology = inputs["topology"]
	# Iterate through the links in the topology
	link_lengths = {}
	for link in topology:
		endpoints = [link["ep1"],link["ep2"]]
		# Compute positions of both link-endpoints
		positions = []
		node_ids = []
		for endpoint in endpoints:
			# Endpoint is a chiplet
			if endpoint["type"] == "chiplet":
				chiplet_desc = placement["chiplets"][endpoint["outer_id"]]
				chiplet = chiplets[chiplet_desc["name"]]
				# Rotate the chiplet if needed  
				chiplet = hlp.rotate_chiplet(chiplet, chiplet_desc["rotation"])
				phy = chiplet["phys"][endpoint["inner_id"]]
				positions.append((chiplet_desc["position"]["x"] + phy["x"],chiplet_desc["position"]["y"] + phy["y"]))
				node_ids.append(("chiplet", endpoint["outer_id"]))
			# Endpoint is an interposer router
			else:
				irouter = placement["interposer_routers"][endpoint["outer_id"]]
				positions.append((irouter["position"]["x"],irouter["position"]["y"]))
				node_ids.append(("irouter", endpoint["outer_id"]))
		# Compute link length
		if packaging["link_routing"] == "manhattan":
			length = sum([abs(positions[0][dim] - positions[1][dim]) for dim in range(2)])
		elif packaging["link_routing"] == "euclidean":
			length =  math.sqrt(sum([abs(positions[0][dim] - positions[1][dim])**2 for dim in range(2)]))
		link_lengths[tuple(node_ids)] = length
		link_lengths[tuple(reversed(node_ids))] = length
	# Return results
	return link_lengths

def compute_link_latencies(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["packaging","topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	packaging = inputs["packaging"]
	topology = inputs["topology"]
	# Load intermediates if not already loaded
	required_intermediates = ["link_lengths"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_lengths = intermediates["link_lengths"]
	# Compute per-link latencies
	link_latencies = {}
	for link in topology:
		node_id_1 = (link["ep1"]["type"],link["ep1"]["outer_id"])
		node_id_2 = (link["ep2"]["type"],link["ep2"]["outer_id"])
		if packaging["link_latency_type"] == "constant":
			lat = int(math.ceil(packaging["link_latency"]))
		else:
			lat = int(math.ceil(eval(packaging["link_latency"])(link_lengths[(node_id_1,node_id_2)])))
		link_latencies[(node_id_1,node_id_2)] = lat
		link_latencies[(node_id_2,node_id_1)] = lat
	# Return results
	return link_latencies

def compute_link_bandwidths(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","packaging","placement","topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	topology = inputs["topology"]
	# Compute per-link bandwidths
	link_bandwidths = {}
	for link in topology:
		link_bw = float("inf")
		for ep_lab in [x for x in link.keys() if "ep" in x]:
			ep = link[ep_lab]
			if ep["type"] == "chiplet":
				chiplet = chiplets[placement["chiplets"][ep["outer_id"]]["name"]]
				phy = chiplet["phys"][ep["inner_id"]]
				ac = chiplet["dimensions"]["x"] * chiplet["dimensions"]["y"]			# Chiplet area in mm^2
				fp = chiplet["fraction_power_bumps"]									# Fraction of bumps used for power 
				fca = phy["fraction_bump_area"]											# Fraction of bump area	use by PHY
				pb = packaging["bump_pitch"]											# Bump pitch in mm
				ndw = packaging["non_data_wires"]										# Number of non-data wires per link
				lbw = int(math.floor((ac * (1-fp) * fca * (1/pb)**2) - ndw))			# Link bandwidth in bit/cycle
				link_bw = min(link_bw, lbw)
		node_id_1 = (link["ep1"]["type"],link["ep1"]["outer_id"])
		node_id_2 = (link["ep2"]["type"],link["ep2"]["outer_id"])
		link_bandwidths[(node_id_1,node_id_2)] = link_bw / 2.0			# Divide by 2 because each link is counted twice, once in each direction
		link_bandwidths[(node_id_2,node_id_1)] = link_bw / 2.0			# Divide by 2 because each link is counted twice, once in each direction
	# Return results
	return link_bandwidths


def compute_area(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","placement"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	# Smallest and largest coordinates occupied by a chiplet
	(minx, miny, maxx, maxy) = (float("inf"),float("inf"),-float("inf"),-float("inf"))
	# Total area occupied by chiplets
	total_chiplet_area = 0
	# Iterate through chiplets
	for chiplet_desc in placement["chiplets"]:
		chiplet = chiplets[chiplet_desc["name"]]
		(x,y) = (chiplet_desc["position"]["x"],chiplet_desc["position"]["y"])   	# Position
		(w,h) = (chiplet["dimensions"]["x"],chiplet["dimensions"]["y"])		 		# Dimensions
		# Add this chiplets area to total area
		total_chiplet_area += (w * h)
		# Update min and max coordinates
		(minx, miny, maxx, maxy) = (min(minx, x), min(miny, y), max(maxx, x + w), max(maxy, y + h))
	# Consider interposer routers for area computation
	for irouter in placement["interposer_routers"]:
		(x,y) = (irouter["position"]["x"],irouter["position"]["y"])   	# Position
		(minx, miny, maxx, maxy) = (min(minx, x), min(miny, y), max(maxx, x), max(maxy, y))
	# Compute total interposer area
	chip_width = (maxx - minx)
	chip_height = (maxy - miny)
	total_interposer_area =  chip_width * chip_height
	# Aggregate results
	area = {
		"chip_width" : chip_width,
		"chip_height" : chip_height,
		"total_chiplet_area" : total_chiplet_area,
		"total_interposer_area" : total_interposer_area
	}
	# Return results
	return area


################################################################################################################
# Outputs
################################################################################################################

def compute_area_summary(inputs, intermediates):
	# Compute intermediates if not already computed
	required_intermediates = ["area"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	area = intermediates["area"]
	print("Computing area summary...") if inputs["verbose"] else None
	# Return results
	return area

def compute_power_summary(inputs, intermediates):
	design = inputs["design"]
	# Load inputs if not already loaded
	required_inputs = ["chiplets","packaging","placement"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	# Compute intermediates if not already computed
	required_intermediates = ["link_lengths"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_lengths = intermediates["link_lengths"]
	print("Computing power summary...") if inputs["verbose"] else None
	# Compute power consumption of chiplets
	total_chiplet_power = sum([chiplets[chiplet_desc["name"]]["power"] for chiplet_desc in placement["chiplets"]])
	# Compute power consumption of interposer routers
	if packaging["is_active"]:
		total_interposer_power = len(placement["interposer_routers"]) * packaging["power_irouter"]
	else:
		total_interposer_power = 0
	# Compute power of links - We divide by 2 because each link is counted twice, once in each direction
	if packaging["link_power_type"] == "constant":
		total_link_power = len(link_lengths) * packaging["link_power"] / 2
	else:
		total_link_power = sum([eval(packaging["link_power"])(link_length) for link_length in link_lengths.values()]) / 2
	# Compute total interposer area
	total_power = total_chiplet_power + total_interposer_power
	# Aggregate the results
	power_summary = {
		"total_power" : total_power,
		"total_chiplet_power" : total_chiplet_power,
		"total_interposer_power" : total_interposer_power
	}
	# Return results
	return power_summary

def compute_link_summary(inputs, intermediates):
	# Compute intermediates if not already computed
	required_intermediates = ["link_lengths", "link_bandwidths"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_lengths = intermediates["link_lengths"]
	link_bandwidths = intermediates["link_bandwidths"]
	print("Computing link summary...") if inputs["verbose"] else None
	link_summary = {}
	for metric in ["lengths", "bandwidths"]:
		data = {"lengths" : link_lengths, "bandwidths" : link_bandwidths}[metric]
		# Compute a histogram of link lengths/bandwidths, round lengths to 1um (lengths are in mm) and bandwidths to 0.001 bit/cycle
		histogram = {}
		for link in [link for link in data.keys() if link[0] < link[1]]:
			value = round(data[link],3)
			if value not in histogram:
				histogram[value] = 0
			histogram[value] += 1
		# Aggregate results
		summary = {
			"min" : min(histogram.keys()),
			"avg" : sum(data.values()) / len(data),
			"max" : max(histogram.keys()),
			"histogram" : histogram
		}
		link_summary[metric] = summary
	return link_summary

def compute_cost(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","packaging","placement","technologies"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	technologies = inputs["technologies"]
	# Compute intermediates if not already computed
	required_intermediates = ["area"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	area = intermediates["area"]
	print("Computing manufacturing cost...") if inputs["verbose"] else None
	# First, compute the manufacturing cost per chiplet
	cost_per_chiplet = {}
	for chiplet_name in set([x["name"] for x in placement["chiplets"]]):
		chiplet = chiplets[chiplet_name]
		tech = technologies[chiplet["technology"]]
		cost_per_chiplet[chiplet_name] = {}
		wr = tech["wafer_radius"]									   	# Wafer radius
		dd = tech["defect_density"]									 	# Defect density
		wc = tech["wafer_cost"]										 	# Wafer cost
		ca = chiplet["dimensions"]["x"] * chiplet["dimensions"]["y"]	# Chiplet area
		# Dies per wafer
		dies_per_wafer = int(math.floor(((math.pi * wr**2) / ca) - ((math.pi * 2 * wr) / math.sqrt(2 * ca))))
		cost_per_chiplet[chiplet_name]["dies_per_wafer"] = dies_per_wafer
		# Manufacturing yield
		manufacturing_yield = 1.0 / (1.0 + dd * ca)
		cost_per_chiplet[chiplet_name]["manufacturing_yield"] = manufacturing_yield
		# Known good dies
		known_good_dies = dies_per_wafer * manufacturing_yield
		cost_per_chiplet[chiplet_name]["known_good_dies"] = known_good_dies
		# Cost
		cost = wc / known_good_dies
		cost_per_chiplet[chiplet_name]["cost"] = cost
	# Next, compute the manufacturing cost of the interposer if an interposer is used
	cost_interposer = {"cost" : 0}
	if packaging["has_interposer"]:
		ip_tech = technologies[packaging["interposer_technology"]]
		wr = ip_tech["wafer_radius"]									# Wafer radius
		dd = ip_tech["defect_density"]							  		# Defect density
		wc = ip_tech["wafer_cost"]								  		# Wafer cost
		ia = area["total_interposer_area"]					  			# Interposer area
		# Dies per wafer
		dies_per_wafer = int(math.floor(((math.pi * wr**2) / ia) - ((math.pi * 2 * wr) / math.sqrt(2 * ia))))
		cost_interposer["dies_per_wafer"] = dies_per_wafer
		# Manufacturing yield
		manufacturing_yield = 1.0 / (1.0 + dd * ia)
		cost_interposer["manufacturing_yield"] = manufacturing_yield
		# Known good dies
		known_good_dies = dies_per_wafer * manufacturing_yield
		cost_interposer["known_good_dies"] = known_good_dies
		# Cost
		cost = (wc / known_good_dies) if known_good_dies > 0 else float("nan")
		cost_interposer["cost"] = cost
	# Compute the overall cost per working chip
	py = packaging["packaging_yield"]								   # Packaging yield
	total_cost = (sum([cost_per_chiplet[x["name"]]["cost"] for x in placement["chiplets"]]) + cost_interposer["cost"]) / py
	# Aggregate results
	cost_summary = {
		"total_cost" : total_cost,
		"interposer" : cost_interposer,
		"chiplets" : cost_per_chiplet
	}
	# Return results
	return cost_summary

def compute_latency(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","packaging","placement","routing_table","technologies","traffic_by_chiplet"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	packaging = inputs["packaging"]
	placement = inputs["placement"]
	routing_table_ = inputs["routing_table"]
	routing_table_type = routing_table_["type"]
	routing_table = routing_table_["table"]
	technologies = inputs["technologies"]
	traffic_by_chiplet = inputs["traffic_by_chiplet"]
	# Compute intermediates if not already computed
	required_intermediates = ["link_latencies"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_latencies = intermediates["link_latencies"]
	print("Computing latency...") if inputs["verbose"] else None
	# Compute relay-latency (for intermediate nodes) and latency (for endpoints) of each node
	node_latencies = {}
	node_relay_latencies = {}
	# Add relay-latency of interposer-routers (they do not have a regular latency, as they can't be endpoints)
	lat_ir = packaging["latency_irouter"]
	for rid in range(len(placement["interposer_routers"])):
		node_relay_latencies[("irouter",rid)] = lat_ir
	# Add latency and relay-latency of chiplets
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		lat_int = chiplet["internal_latency"]
		lat_phy = technologies[chiplet["technology"]]["phy_latency"]
		node_latencies[("chiplet",cid)] = lat_int + lat_phy
		node_relay_latencies[("chiplet",cid)] = lat_phy + lat_int + lat_phy
	# The average latency under the specified routing and traffic
	min_latency = float("inf")	
	max_latency = -float("inf")
	sum_of_weghted_latencies = 0
	sum_of_weights = 0
	# Iterate through pairs of communicating chiplets
	for (sid, did) in traffic_by_chiplet.keys():
		src_node = ("chiplet",sid)
		dst_node = ("chiplet",did)
		# Latency of sending a packet from the source node to the centra router of the source chiplet
		lat = 1
		# Latency of source chiplet's central router
		lat += node_latencies[("chiplet",sid)]
		# Latency of links and intermediate nodes
		prv_node = "-1"
		cur_node = src_node
		while cur_node != dst_node:
			if routing_table_type == "default":
				nxt_node = tuple(routing_table[cur_node][dst_node])
			elif routing_table_type == "extended":
				nxt_node = tuple(routing_table[cur_node][dst_node][prv_node])
			else:
				print("ERROR: Unknown routing table type %s" % routing_table_type)
				sys.exit(1)	
			# Add link latency
			lat += link_latencies[(cur_node,nxt_node)]
			# Add relay latency
			if nxt_node != dst_node:
				lat += node_relay_latencies[nxt_node]
			# Move to the next node
			prv_node = cur_node
			cur_node = nxt_node
		# Latency of destination chiplet's central router
		lat += node_latencies[("chiplet",did)]
		# Latency of sending a packet from the destination chiplet's central router to the destination node
		lat += 1
		# Finally, one cycle to eject the packet at the destination node
		lat += 1
		# Update the average latency
		min_latency = min(min_latency, lat)
		max_latency = max(max_latency, lat)
		sum_of_weghted_latencies += lat * traffic_by_chiplet[(sid,did)]
		sum_of_weights += traffic_by_chiplet[(sid,did)]
	# Compute the average latency	
	avg_latency = sum_of_weghted_latencies / sum_of_weights
	# Aggregate results
	latency = {
		"min" : min_latency,
		"avg" : avg_latency,
		"max" : max_latency
	}
	# Return results
	return latency

def compute_throughput(inputs, intermediates):
	# Load inputs if not already loaded
	required_inputs = ["routing_table","topology","traffic_by_chiplet"]
	hlp.read_required_inputs(inputs, required_inputs)
	routing_table_ = inputs["routing_table"]
	routing_table_type = routing_table_["type"]
	routing_table = routing_table_["table"]
	topology = inputs["topology"]
	traffic_by_chiplet = inputs["traffic_by_chiplet"]
	# Compute intermediates if not already computed
	required_intermediates = ["link_bandwidths"]
	hlp.compute_required_intermediates(inputs, intermediates, required_intermediates)
	link_bandwidths = intermediates["link_bandwidths"]
	print("Computing throughput...") if inputs["verbose"] else None
	# Compute per-link load under an injection rate of 1.0
	link_loads = {}
	# Initialize link loads with zero
	for link in topology:
		node_id_1 = (link["ep1"]["type"],link["ep1"]["outer_id"])
		node_id_2 = (link["ep2"]["type"],link["ep2"]["outer_id"])
		link_loads[(node_id_1,node_id_2)] = 0
		link_loads[(node_id_2,node_id_1)] = 0
	# Iterate through communicating chiplets and add link-loads on the path
	for (sid, did) in traffic_by_chiplet.keys():
		src_node = ("chiplet",sid)
		dst_node = ("chiplet",did)
		prv_node = "-1"
		cur_node = src_node
		while cur_node != dst_node:
			if routing_table_type == "default":
				nxt_node = tuple(routing_table[cur_node][dst_node])
			elif routing_table_type == "extended":
				nxt_node = tuple(routing_table[cur_node][dst_node][prv_node])
			else:
				print("ERROR: Unknown routing table type %s" % routing_table_type)
				sys.exit(1)	
			# Add the traffic load to the link
			link_loads[(cur_node,nxt_node)] += traffic_by_chiplet[(sid,did)]
			# Move to the next node
			prv_node = cur_node
			cur_node = nxt_node
	# Find the link-throughputs 	
	link_throughputs = {link : (link_bandwidths[link] / link_loads[link]) if link_loads[link] > 0 else float("inf") for link in link_loads.keys()}
	# Find the per-flow throughputs
	max_link_bandwidth = max(link_bandwidths.values()) 
	# Iterate through communicating chiplets and sum up global throughput
	# TODO: Old
	"""
	min_throughput_per_traffic_unit = float("inf")
	for (sid, did) in traffic_by_chiplet.keys():
		src_node = ("chiplet",sid)
		dst_node = ("chiplet",did)
		prv_node = "-1"
		cur_node = src_node
		flow_throughput_per_traffic_unit = max_link_bandwidth
		#flow_throughput = min(flow_throughput, router_throughputs[cur_node])
		while cur_node != dst_node:
			if routing_table_type == "default":
				nxt_node = tuple(routing_table[cur_node][dst_node])
			elif routing_table_type == "extended":
				nxt_node = tuple(routing_table[cur_node][dst_node][prv_node])
			else:
				print("ERROR: Unknown routing table type %s" % routing_table_type)
				sys.exit(1)	
			# Add the traffic load to the link
			flow_throughput_per_traffic_unit = min(flow_throughput_per_traffic_unit, link_throughputs[(cur_node,nxt_node)])
			# Move to the next node
			prv_node = cur_node
			cur_node = nxt_node
		min_throughput_per_traffic_unit = min(min_throughput_per_traffic_unit, flow_throughput_per_traffic_unit)
	"""
	# TODO: New
	min_throughput_per_traffic_unit = min(link_throughputs.values())	
	aggregate_load = sum(traffic_by_chiplet.values())
	# Compute the aggregate throughput in bits/cycle
	aggregate_throughput = min_throughput_per_traffic_unit * aggregate_load
	# Aggregate results
	throughput = {
		"aggregate_throughput" : aggregate_throughput,
	}
	# Return results
	return throughput


def perform_booksim_simulation(inputs, intermediates):
	run_identifier = inputs["design"]["design_name"]
	# Read inputs if not already loaded	
	required_inputs = ["booksim_config"]
	hlp.read_required_inputs(inputs, required_inputs)
	booksim_config = inputs["booksim_config"]
	# Export the design to BookSim
	port_map = bsw.export_booksim_topology(inputs, intermediates, run_identifier)
	bsw.export_routing_table(inputs, intermediates, port_map, run_identifier)
	if booksim_config["mode"] == "traffic":
		bsw.export_traffic(inputs, intermediates, run_identifier)
	else:
		bsw.export_trace(inputs, intermediates, run_identifier)
	# Perform the BookSim simulation
	print("Performing BookSim simulation...") if inputs["verbose"] else None
	bs_results = bsw.run_booksim_simulation(inputs, intermediates, run_identifier)
	# Return the results
	return bs_results


def rapidchiplet(inputs, intermediates, do_compute, results_file, verbose = False, validate = True):
	total_start_time = time.time()
	# Store verbose option in inputs
	inputs["verbose"] = verbose
	inputs["validate"] = validate
	# Initialize outputs
	outputs = {}
	# Compute the selected metrics
	for metric in metrics:
		if do_compute[metric] and metric not in outputs:
			start_time = time.time()
			outputs[metric] = metric_computation_functions[metric](inputs, intermediates)
			end_time = time.time()
			outputs[metric]["time_taken"] = end_time - start_time
	# Store time taken
	outputs["total_time_taken"] = time.time() - total_start_time
	return outputs

# Define all metrics supported by RapidChiplet
metrics = ["area_summary", "power_summary", "link_summary", "cost", "latency", "throughput", "booksim_simulation"]

# Define all functions that compute the metrics and the metrics themselves
metric_computation_functions = {
	# Intermediates
	"link_lengths" : compute_link_lengths,
	"link_latencies" : compute_link_latencies,
	"link_bandwidths" : compute_link_bandwidths,
	"area" : compute_area,
	# Outputs
	"area_summary" : compute_area_summary,
	"power_summary" : compute_power_summary,
	"link_summary" : compute_link_summary,
	"cost" : compute_cost,
	"latency" : compute_latency,
	"throughput" : compute_throughput,
	"booksim_simulation" : perform_booksim_simulation,
}

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file")
	parser.add_argument("-rf", "--results_file", required = True, help = "Name of the results file (is stored in ./outputs/)")
	parser.add_argument("-as", "--area_summary", action="store_true", help = "Compute the area summary")
	parser.add_argument("-ps", "--power_summary", action="store_true", help = "Compute the power summary")
	parser.add_argument("-ls", "--link_summary", action="store_true", help = "Compute the link summary")
	parser.add_argument("-c", "--cost", action="store_true", help = "Compute the manufacturing cost")
	parser.add_argument("-l", "--latency", action="store_true", help = "Compute the ICI latency")
	parser.add_argument("-t", "--throughput", action="store_true", help = "Compute the ICI throughput")
	parser.add_argument("-bs", "--booksim_simulation", action="store_true", help = "Simulate the design using BookSim")
	parser.add_argument("-nv", "--no_validation", action="store_true", help = "Skip the validation of the design")
	args = parser.parse_args()
	do_compute = {metric : getattr(args, metric) for metric in metrics}
	validate = not args.no_validation
	# Read the design file
	inputs = {"design" : hlp.read_json(filename = args.design_file)}
	intermediates = {}
	# Run the main function
	results = rapidchiplet(inputs, intermediates, do_compute, args.results_file, verbose = True, validate = validate)
	# Store results
	hlp.write_json("./results/%s.json" % args.results_file, results)

