# Import python libraries
import os
import sys
import copy
import math
import argparse

# Import RapidChiplet files
import helpers as hlp

def validate_design(design, technology = None, chiplets = None, placement = None, topology = None, packaging = None, thermal_config = None, booksim_config = None):
	errors = 0
	# Validate the technology_nodes-file
	if technology != None:
		for (tech_name, tech) in technology.items():
			# The PHY latency must be positive
			if tech["phy_latency"] <= 0:
				print("validation error: Invalid PHY latency \"%s\" of technology \"%s\", this parameter must be positive." % (tech["phy_latency"], tech_name))
				errors += 1
			# The wafer radius must be positive
			if tech["wafer_radius"] <= 0:
				print("validation error: Invalid wafer radius \"%s\" of technology \"%s\", this parameter must be positive." % (tech["wafer_radius"], tech_name))
				errors += 1
			# The wafer cost must be non-negative
			if tech["wafer_cost"] < 0:
				print("validation error: Invalid wafer cost \"%s\" of technology \"%s\", this parameter must be non-negative." % (tech["wafer_cost"], tech_name))
				errors += 1
			# The defect density needs to be between 0.0 and 1.0
			if tech ["defect_density"] < 0.0 or tech["defect_density"] > 1.0:
				print("validation error: Invalid defect density \"%s\" of technology \"%s\", this parameter must be between 0.0 and 1.0." % (tech["defect_density"], tech_name))
				errors += 1
	# Validate the chiplets-file
	if chiplets != None:
		if technology == None:
			technology = hlp.read_file(filename = design["technology_nodes_file"])
		for (chiplet_name, chiplet) in chiplets.items():
			# Dimensions must be larger than zero
			if min(chiplet["dimensions"]["x"], chiplet["dimensions"]["x"]) <= 0:
				print("validation error: Invalid dimensions \"%s\" of chiplet \"%s\", dimensions must be positive." % (str(chiplet["dimensions"]), chiplet_name))
				errors += 1
			# Type bust be compute, memory, or io
			if chiplet["type"] not in ["compute","memory","io"]:	
				print("validation error: Chiplet \"%s\" has an invalid type: \"%s\" (only \"compute\", \"memory\", or \"io\" are allowed.)" % (chiplet_name, chiplet["type"]))
				errors += 1
			# Technology node must be present in technology nodes file
			if chiplet["technology"] not in technology:
				print("validation error: The technology \"%s\" used in chiplet \"%s\" has not been specified in the technology file" % (chiplet["technology"], chiplet_name))
				errors += 1
			# The internal latency must be positive
			if chiplet["internal_latency"] <= 0:
				print("validation error: Invalid relay latency \"%s\" of chiplet \"%s\", this parameter must be positive. If not used, set to NaN." % (chiplet["internal_latency"], chiplet_name))
				errors += 1
			# The unit count must be an integer and at least 1
			if chiplet["unit_count"] % 1 != 0 or chiplet["unit_count"] < 1:
				print("validation error: Invalid unit count \"%s\" of chiplet \"%s\", this parameter must be an integer and at least 1." % (chiplet["unit_count"], chiplet_name))
				errors += 1
	# Validate the chiplet_placement-file: Chiplets need to be non-overlapping
	# Check all pairs of chiplets
	if placement != None:
		if chiplets == None:
			print("validation error: validating the placement-file requires the corresponding chiplets-file -> reading chiplets file.")
			chiplets = hlp.read_file(filename = design["chiplets_file"])
		for c1 in range(len(placement["chiplets"])-1):
			chiplet_desc_1 = placement["chiplets"][c1]
			chiplet_1 = chiplets[chiplet_desc_1["name"]]
			# Rotate the chiplet if needed
			chiplet_1 = hlp.rotate_chiplet(chiplet_1, chiplet_desc_1["rotation"])
			# Extract info
			(x1,y1) = (chiplet_desc_1["position"]["x"], chiplet_desc_1["position"]["y"])		# x and y position
			(w1,h1) = (chiplet_1["dimensions"]["x"], chiplet_1["dimensions"]["y"])				# with and height
			(l1,r1,t1,b1) = (x1, x1 + w1, y1, y1 + h1)											# left, right, top, bottom
			for c2 in range(c1+1, len(placement["chiplets"])):
				chiplet_desc_2 = placement["chiplets"][c2]
				chiplet_2 = chiplets[chiplet_desc_1["name"]]
				# Rotate the chiplet if needed
				chiplet_2 = hlp.rotate_chiplet(chiplet_2, chiplet_desc_2["rotation"])
				# Extract info
				(x2,y2) = (chiplet_desc_2["position"]["x"], chiplet_desc_2["position"]["y"])	# x and y position
				(w2,h2) = (chiplet_2["dimensions"]["x"], chiplet_2["dimensions"]["y"]) 			# with and height
				(l2,r2,t2,b2) = (x2, x2 + w2, y2, y2 + h2)										# left, right, top, bottom
				# Check for overlap
				if not ((r1 <= l2) or (r2 <= l1) or (t1 <= b2) or (t2 <= b1)):
					print("validation error: Chiplets %d and %d are overlapping" % (c1, c2))
					errors += 1
	# Validate the topology: Check that only valid chiplets/phys or interposer-routers/ports are referenced and that each port is referenced only once
	if topology != None:
		if chiplets == None:
			print("validation error: validating the topology-file requires the corresponding chiplets-file -> reading chiplets file.")
			chiplets = hlp.read_file(filename = design["chiplets_file"])
		if placement == None:
			print("validation error: validating the topology-file requires the corresponding placement-file -> reading placement file.")
			placement = hlp.read_file(filename = design["chiplet_placement_file"])
		used_phys = []
		used_ports = []
		for (lid, link) in enumerate(topology):
			endpoints = [link["ep1"],link["ep2"]]
			for ep in endpoints:
				if ep["type"] not in ["chiplet","irouter"]:
					print("validation error: Invalid link-endpoint type \"%s\" for link %d. The endpoint type must be \"chiplet\" or \"irouter\"." % (ep["type"], lid))
					errors += 1
				if ep["type"] == "chiplet":
					# Check that the chiplet-id is valid
					if ep["outer_id"] >= len(placement["chiplets"]):
						print("validation error: Invalid chiplet-id \"%s\" for link %d. There are only %d chiplets." % (ep["outer_id"], lid, len(placement["chiplets"])))
						errors += 1
					# Check that the PHY-id is valid
					elif ep["inner_id"] >= len(chiplets[placement["chiplets"][ep["outer_id"]]["name"]]["phys"]):
						print("validation error: Invalid PHY-id \"%s\" for link %d. There are not that many PHYS in the chiplet with id %s." % (ep["inner_id"], lid, ep["outer_id"]))
						errors += 1
					# Check that each PHY is only used once
					elif (ep["outer_id"],ep["inner_id"]) in used_phys:
						print("validation error: The PHY number %s of the chiplet with id %s is used multiple times (in link %d)." % (ep["inner_id"], ep["outer_id"], lid))
						errors += 1
					# Remember that this PHY has been used
					else:
						used_phys.append((ep["outer_id"],ep["inner_id"]))
				if ep["type"] == "irouter":
					# Check that the interposer-router-id is valid
					if ep["outer_id"] >= len(placement["interposer_routers"]):
						print("validation error: Invalid interposer-router-id \"%s\" for link %d. There are only %d interposer-routers." % (ep["outer_id"], lid, len(placement["interposer_routers"])))
						errors += 1
					# Check that the port-id is valid
					elif ep["inner_id"] >= placement["interposer_routers"][ep["outer_id"]]["ports"]:
						print("validation error: Invalid port-id \"%s\" for link %d. There are not that many ports in the interposer-router with id %s." % (ep["inner_id"], lid, ep["outer_id"]))
						errors += 1
					# Check that each port is only used once
					elif (ep["outer_id"],ep["inner_id"]) in used_ports:
						print("validation error: The port number %s of the interposer-router with id %s is used multiple times (in link %d)." % (ep["inner_id"], ep["outer_id"], lid))
						errors += 1
					# Remember that this PHY has been used
					else:
						used_ports.append((ep["outer_id"],ep["inner_id"]))
	# Validate the packaging: 
	# Link routing must be manhattan or eucledian
	if packaging != None:
		if packaging["link_routing"] not in ["manhattan", "euclidean"]:
			print("validation error: Invalid link routing \"%s\", only \"manhattan\" and \"euclidean\" are allowed." % packaging["link_routing"])
			errors += 1
		if packaging["link_latency_type"] not in ["constant", "function"]:
			print("validation error: Invalid link latency type \"%s\", only \"constant\" and \"function\" are allowed." % packaging["link_latency_type"])
			errors += 1
		if packaging["link_latency_type"] == "constant":
			if packaging["link_latency"] < 1 or packaging["link_latency"] % 1 != 0:
				print("validation error: Invalid link latency \"%s\". This parameter must be an integer larger than 0" % packaging["link_latency"])
				errors += 1
		if packaging["link_latency_type"] == "function":
			try:
				tmp = int(math.ceil(eval(packaging["link_latency"])(3)))
			except:
				print("validation error: Invalid link latency function \"%s\". Unable to evaluate function." % packaging["link_latency"])
				errors += 1
		# The packaging yield must be between 0.0 and 1.0
		if packaging["packaging_yield"] < 0.0 or packaging["packaging_yield"] > 1.0:
			print("validation error: Invalid packaging yield \"%s\". This parameter must be between 0.0 and 1.0." % packaging["packaging_yield"])
			errors += 1
		# Check that active interposers contain the required information
		if packaging["is_active"]:
			# Validate interposer-router latency: Must be present and non-negative
			if "latency_irouter" not in packaging:
				print("validation error: Active interposers must specify the parameter \"latency_iroute\"")
				errors += 1
			elif packaging["latency_irouter"] < 0:
				print("validation error: Invalid interposer-router latency \"%s\". This parameter must not be negative." % packaging["latency_irouter"])
				errors += 1
			# Validate interposer-router power consumption: Must be present and non-negative
			if "power_irouter" not in packaging:
				print("validation error: Active interposers must specify the parameter \"power_irouter\"")
				errors += 1
			elif packaging["power_irouter"] < 0:
				print("validation error: Invalid interposer-router power consumption \"%s\". This parameter must not be negative." % packaging["power_irouter"])
				errors += 1
		# Check that interposers contain the required information
		if packaging["has_interposer"]:
			# The wafer radius must be positive
			if "interposer_technology" not in packaging:
				print("validation error: Packages with interposers must specify the parameter \"interposer_technology\"")
				errors += 1
			elif packaging["interposer_technology"] not in technology:
				print("validation error: Interposer Technology \"%s\" not found in technology-file." % packaging["interposer_technology"])
				errors += 1
	if thermal_config != None:	
	# The parameter k_t must be below 0.25, otherwise the thermal simulation is unstable
		if thermal_config["k_t"] >= 0.25:
			print("validation error: The parameter k_t in the thermal config must be below 0.25, otherwise, the simulation is unstable.")
			errors += 1
	# Return true if the design is valid and false otherwise
	return errors == 0

def validate_ici_graph(ici_graph):
	(c, r, n, neighbors, relay_map, nodes_by_type) = ici_graph
	# Check for unconnected chiplets or irouters
	for node in range(n):
		if len(neighbors[node]) == 0:
			print("validation error: Node %d is not connected." % node)
	# Check for a fully connected topology: Run BFS
	cur = 0
	todo = [cur]	
	visited_count = 0
	visited = [False for i in range(n)]
	discovered = [False for i in range(n)]
	discovered[0] = True
	while len(todo) > 0 and visited_count < n:
		cur = todo.pop(0)
		if visited[cur]:
			print("ERROR: This is a bug in the BFS implementation of the ici-graph validation function.")
			continue
		visited[cur] = True
		visited_count += 1
		for nei in neighbors[cur]:
			if (not visited[nei]) and (not discovered[nei]):
				todo.append(nei)
				discovered[nei] = True
	if visited_count != n:
		print("validation error: The topology is not fully connected.")
		return False
	else:
		return True

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()	
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file") 
	args = parser.parse_args()
	# Read the design file
	design = hlp.read_file(filename = args.design_file)
	# Read the remaining files
	technology = hlp.read_file(filename = design["technology_nodes_file"])
	chiplets = hlp.read_file(filename = design["chiplets_file"])
	placement = hlp.read_file(filename = design["chiplet_placement_file"])
	topology = hlp.read_file(filename = design["ici_topology_file"])
	packaging = hlp.read_file(filename = design["packaging_file"])
	thermal_config = hlp.read_file(filename = design["thermal_config"])
	# Validate the design
	validate_design(design, technology, chiplets, placement, topology, packaging, thermal_config)

