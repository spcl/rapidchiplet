# Import python libraries
import time
import subprocess

# Import RapidChiplet files
import helpers as hlp
import design_generator as dgen
import plots

# Generate a series of mesh-designs with different scales
def generate_mesh_designs(chiplets, max_size):
	# Setup for mesh
	c_phy_map = {"N" : 0, "E" : 1, "S" : 2, "W" : 3}
	m_phy_map = {"N" : 0}
	i_phy_map = {"N" : 0}
	# Create some mesh topologies:
	names = []
	scales = []
	# Iterate through scales
	for x in range(2,max_size + 1):
		name = "mesh_%dx%d" % (x,x)	
		names.append(name)
		scales.append(x)
		(placement, topology) = dgen.generate_mesh(x, x, chiplets, "compute_chiplet_4phys", c_phy_map, "memory_chiplet_square", m_phy_map, "io_chiplet_square", i_phy_map)
		hlp.write_file("inputs/chiplet_placements/%s.json" % name, placement)
		hlp.write_file("inputs/ici_topologies/%s.json" % name, topology)
		design = {
			"technology_nodes_file" : "inputs/technology_nodes/example_technologies.json",
			"chiplets_file" : "inputs/chiplets/example_chiplets.json",
			"chiplet_placement_file" : "inputs/chiplet_placements/%s.json" % name,
			"ici_topology_file" : "inputs/ici_topologies/%s.json" % name,
			"packaging_file" : "inputs/packaging/example_packaging_passive.json",
			"thermal_config" : "inputs/thermal_config/example_thermal_config.json",
			"booksim_config" : "inputs/booksim_config/example_booksim_config.json"
		}
		hlp.write_file("inputs/designs/%s.json" % name, design)
	return list(zip(names, scales))

# Generate a series of concentrated-mesh-designs with different scales
def generate_cmesh_designs(chiplets, max_size):
	# Setup for mesh
	c_phy_map = {"N" : 0, "E" : 0, "S" : 0, "W" : 0}
	m_phy_map = {"N" : 0}
	i_phy_map = {"N" : 0}
	# Create some concentrated mesh topologies:
	names = []
	scales = []
	# Iterate through scales
	for x in range(1,int(max_size / 2) + 1):
		name = "cmesh_%dx%d" % (2*x,2*x)	
		names.append(name)
		scales.append(2*x)
		(placement, topology) = dgen.generate_concentrated_mesh(x, x, 4, chiplets, "compute_chiplet_1phy", c_phy_map, "memory_chiplet_square", m_phy_map, "io_chiplet_square", i_phy_map)
		hlp.write_file("inputs/chiplet_placements/%s.json" % name, placement)
		hlp.write_file("inputs/ici_topologies/%s.json" % name, topology)
		design = {
			"technology_nodes_file" : "inputs/technology_nodes/example_technologies.json",
			"chiplets_file" : "inputs/chiplets/example_chiplets.json",
			"chiplet_placement_file" : "inputs/chiplet_placements/%s.json" % name,
			"ici_topology_file" : "inputs/ici_topologies/%s.json" % name,
			"packaging_file" : "inputs/packaging/example_packaging_active.json",
			"thermal_config" : "inputs/thermal_config/example_thermal_config.json",
			"booksim_config" : "inputs/booksim_config/example_booksim_config.json"
		}
		hlp.write_file("inputs/designs/%s.json" % name, design)
	return list(zip(names, scales))

def reproduce_results_from_paper(reps, max_size):
	# Read the chiplets file
	chiplets = hlp.read_file("inputs/chiplets/example_chiplets.json")
	# Generate designs
	designs_mesh = generate_mesh_designs(chiplets, max_size)
	designs_cmesh = generate_cmesh_designs(chiplets, max_size)
	designs = designs_mesh + designs_cmesh
	# Evaluate all designs using RapidChiplet
	for (design, scale) in designs_mesh + designs_cmesh:
		print("Evaluating %s using RapidChiplet" % design)
		design_path = "inputs/designs/%s.json" % design
		for rep in range(reps):
			result_file = design + "_" + str(rep)
			start_time = time.time()	
			out = subprocess.check_output(["python3", "rapid_chiplet.py", "-df", design_path, "-rf", result_file, "-as", "-ps", "-ls", "-as", "-c", "-l", "-t"])
			print("Time taken: %.6f seconds" % (time.time() - start_time))
	# Evaluate all designs using BookSim.
	for traffic in ["C2C","C2M","C2I","M2I"]:
		for (design, scale) in designs:
			print("Evaluating %s using BookSim with %s traffic" % (design, traffic))
			booksim_config = hlp.read_file("inputs/booksim_config/example_booksim_config.json")
			booksim_config["traffic"] = traffic
			booksim_config["sample_period"] = int(500 + (4500 / 14 * (scale-2)))
			hlp.write_file("inputs/booksim_config/example_booksim_config.json",booksim_config)
			design_path = "inputs/designs/%s.json" % design
			result_file = "sim_" + design + "_" + traffic
			start_time = time.time()	
			out = subprocess.check_output(["python3", "run_booksim_simulation.py", "-df", design_path, "-rf", result_file])
			print("Time taken: %.6f seconds" % (time.time() - start_time))
	# Create plots
	plots.reproduce_plots_from_paper(reps, max_size)

# Use 10 repetitions and a maximum size of 16x16 compute-chiplets.
reproduce_results_from_paper(10, 16)

