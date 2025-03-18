# Import python libraries
import sys
import math
import copy

# Import RapidChiplet files
import helpers as hlp
import generate_chiplet as cgen
import generate_placement as pgen
import generate_topology as tgen
import generate_routing as rgen
import generate_traffic as trgen 
import inputs.trace_to_traffic as t2t

# Generates most of the RapidChiplet input files
# Files automatically written: chiplets, design, placement, routing_table, topology, traffic_by_unit, traffic_by_chiplet
# Files modified based on the existing file: booksim_config
# Files not written by the script (must be written manually): technologies, packaging
def generate_inputs(params, design_name, do_write = True):
	params = copy.deepcopy(params)
	# Prepare data to return
	files = {}
	# Gather the design parameters
	use_memory = params["use_memory"]
	topology_name = params['topology']
	placement_name = tgen.topology_to_placement[topology_name]
	phy_placement = tgen.topology_to_phy_placement[topology_name]
	# Convert the string defining the scale to the placement-dependent parameters
	if placement_name in ["grid"]:
		try:
			(rows, cols) = params["grid_scale"].split("x")
			params["rows"] = int(rows)
			params["cols"] = int(cols)
		except:
			print("ERROR: The %s topology requires a %s placement which requires a scale of the format \"<rows>x<cols>\"." % (topology_name, placement_name), end = " ")
			print("The scale \"%s\" is not in the correct format." % params["scale"])
	elif placement_name in ["hexagonal"]:
		try:
			radius = int(params["hex_scale"])
			params["radius"] = int(radius)
		except:
			print("ERROR: The %s topology requires a %s placement which requires a scale of the format \"<radius>\"." % (topology_name, placement_name), end = " ")
			print("The scale \"%s\" is not in the correct format." % params["scale"])
	else:
		print("ERROR: The placement \"%s\" is not supported by the script \"generate_inputs.py\"." % placement_name)
		sys.exit(1)
	# Adjust the PHY-placement to the scale of the design if this is necessary
	if phy_placement == "xPHY_yPHY":
		if topology_name == "flattened_butterfly":
			phy_placement = "%dPHY_%dPHY" % (params["cols"]-1, params["rows"]-1)
		elif topology_name == "hypercube":
			phy_placement = "%dPHY_%dPHY" % (int(math.ceil(math.log2(params["cols"]))), int(math.ceil(math.log2(params["rows"]))))
		elif "kite" in topology_name:
			phy_placement = "4PHY_0PHY"
		elif "sparse_hamming_graph" in topology_name:
			if "shg_sr" in params and "shg_sc" in params:
				(rows, cols) = (params["rows"], params["cols"])
				phy_cnt_h = [0 for i in range(rows * cols)]
				phy_cnt_v = [0 for i in range(rows * cols)]
				for row in range(rows):
					for col in range(cols):
						src = row * cols + col
						for h in ([1] + params["shg_sr"]):
							ocol = col + h
							if ocol < cols:
								dst = row * cols + ocol
								phy_cnt_h[src] += 1
								phy_cnt_h[dst] += 1
						for h in ([1] + params["shg_sc"]):
							orow = row + h
							if orow < rows:
								dst = orow * cols + col
								phy_cnt_v[src] += 1
								phy_cnt_v[dst] += 1
				phy_placement = "%dPHY_%dPHY" % (max(phy_cnt_h), max(phy_cnt_v))
			else:
				print("ERROR: The topology %s requires the parameters \"shg_sr\" and \"shg_sc\"." % topology_name)
				sys.exit(1)
		else:
			print("The topology %s seems to use the phy placement xPHY_yPHY.")
			print("Please specify the values of x and y in the file generate_inputs.py.")
			sys.exit(1)
	# Prepare the design file
	design = {}
	design["design_name"] = design_name
	# Technologies: Nothing to generate here as the technologies file needs to be written manually.
	design["technologies"] = params["technologies_file"]
	# Generate the chiplet(s)
	chiplets = {}	
	comp_params = copy.deepcopy(params)	
	comp_params["chiplet_type"] = "compute"
	chiplets[design_name] = cgen.generate_chiplet(comp_params, phy_placement)
	if use_memory:
		mem_params = copy.deepcopy(params)
		mem_params["chiplet_type"] = "memory"
		chiplets[design_name + "_memory"] = cgen.generate_chiplet(mem_params, phy_placement)
	hlp.write_json("inputs/chiplets/chiplets_%s.json" % design_name, chiplets) if do_write else None
	files["chiplets"] = chiplets
	design["chiplets"]  = "inputs/chiplets/chiplets_%s.json" % design_name
	# Generate the placement
	pgen_fun = pgen.placement_generation_functions[placement_name]
	placement = pgen_fun(params, chiplets[design_name], design_name, use_memory)
	hlp.write_json("inputs/placements/placement_%s.json" % design_name, placement) if do_write else None
	files["placement"] = placement
	design["placement"] = "inputs/placements/placement_%s.json" % design_name
	# Generate the topology
	tgen_fun = tgen.topology_generation_functions[topology_name]
	topology = tgen_fun(params)
	hlp.write_json("inputs/topologies/topology_%s.json" % design_name, topology) if do_write else None
	files["topology"] = topology
	design["topology"] = "inputs/topologies/topology_%s.json" % design_name
	# Packaging: Nothing to generate here as the packaging file needs to be written manually.
	design["packaging"] = params["packaging_file"]
	# Routing table
	routing_algo = params["routing_algorithm"]
	routing_file = "routing_table_%s" % design_name
	routing_table = rgen.generate_routing(chiplets, placement, topology, routing_algo)
	hlp.write_json("inputs/routing_tables/%s.json" % routing_file, routing_table) if do_write else None
	files["routing_table"] = routing_table
	design["routing_table"] = "inputs/routing_tables/%s.json" % routing_file 
	# Traffic and Trace
	if params["mode"] == "traffic":
		traffic_pattern = params["traffic_pattern"]
		traffic_file = "traffic_%s" % design_name	
		# Traffic parameters depending on design and traffic pattern
		if traffic_pattern == "random_uniform":
			sending_units = ["compute"]
			receiving_units = ["memory"] if use_memory else ["compute"]
			traffic_parameters = (sending_units, receiving_units)
		elif traffic_pattern == "hotspot":
			if "n_hotspot" in params and "p_hotspot" in params:
				traffic_parameters = (params["n_hotspot"], params["p_hotspot"])
			else:
				print("ERROR: The hotspot traffic pattern requires the parameters \"n_hotspot\" and \"p_hotspot\".", end = " ")
				print("Please specify these parameters in the experiment-file.")
				sys.exit(1)
		else:
			traffic_parameters = None	
		(traffic_by_unit, traffic_by_chiplet) = trgen.generate_traffic(chiplets, placement, traffic_pattern, traffic_parameters)
		hlp.write_json("./inputs/traffic_by_unit/%s.json" % traffic_file, traffic_by_unit) if do_write else None
		files["traffic_by_unit"] = traffic_by_unit
		hlp.write_json("./inputs/traffic_by_chiplet/%s.json" % traffic_file, traffic_by_chiplet) if do_write else None
		files["traffic_by_chiplet"] = traffic_by_chiplet
		design["traffic_by_unit"] = "inputs/traffic_by_unit/%s.json" % traffic_file
		design["traffic_by_chiplet"] = "inputs/traffic_by_chiplet/%s.json" % traffic_file
		design["trace"] = "none"
	# Trace
	elif params["mode"] == "trace":
		design["trace"] = "inputs/traces/%s.json" % params["trace"]
		inputs = {"design" : design, "validate" : False, "verbose" : False}
		t2t.trace_to_traffic(design["trace"], params["trace"] + ".json")
		design["traffic_by_unit"] = "inputs/traffic_by_unit/%s.json" % params["trace"]
		design["traffic_by_chiplet"] = "inputs/traffic_by_chiplet/%s.json" % params["trace"]
	else:
		print("Invalid mode: %s" % params["mode"])
		sys.exit(1)
	# BookSim configuration: Use the example configuration as a baseline
	bs_config = hlp.read_json(params["booksim_config_file"])
	# Set the mode to traffic or trace
	bs_config["mode"] = params["mode"]
	# Set the BookSim sample period based on the scale of the design.
	# The formula was empirically derived, s.t., the sample period is just small enough to get stable results.
	n_chiplets = len(placement["chiplets"])
	bs_config["sample_period"] = int(500 + (300 * n_chiplets))
	# Write the BookSim configuration to file
	hlp.write_json("inputs/booksim_configs/booksim_config_%s.json" % design_name, bs_config) if do_write else None
	files["booksim_config"] = bs_config
	design["booksim_config"] = "inputs/booksim_configs/booksim_config_%s.json" % design_name
	# Store the design files
	hlp.write_json("inputs/designs/design_%s.json" % design_name, design) if do_write else None
	files["design"] = design
	return files
		
