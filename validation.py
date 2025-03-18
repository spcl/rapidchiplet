# Import python libraries
import sys
import math

# Import RapidChiplet files
import helpers as hlp

# Print validation error 
def print_validation_error(message, args):
	print("\033[91mVALIDATION ERROR:\033[0m " + message % args)

def validate_chiplets(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["chiplets", "technologies"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	technology = inputs["technologies"]
	print("Validating chiplets...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Iterate over all chiplets
	for (chiplet_name, chiplet) in chiplets.items():
		# Dimensions must be positive
		if min(chiplet["dimensions"]["x"], chiplet["dimensions"]["x"]) <= 0:
			msg = "Invalid dimensions %.3f x %.3f of chiplet type \"%s\". Dimensions must be positive."
			args = (chiplet["dimensions"]["x"], chiplet["dimensions"]["y"], chiplet["type"])
			print_validation_error(msg, args)	
			errors += 1
		# PHYs must be located within the chiplet
		for (phy_id, phy) in enumerate(chiplet["phys"]):
			if phy["x"] < 0 or phy["x"] > chiplet["dimensions"]["x"] or phy["y"] < 0 or phy["y"] > chiplet["dimensions"]["y"]:
				msg = "Invalid location (%.3f, %.3f) of PHY %d in chiplet \"%s\". PHYs must be located within the chiplet."
				args = (phy["x"], phy["y"], phy_id, chiplet_name)
				print_validation_error(msg, args)
				errors += 1
		# The sum of fraction_bump_area of all PHYs must be at most 1.0
		if sum([phy["fraction_bump_area"] for phy in chiplet["phys"]]) > 1.0:
			msg = "The sum of fraction_bump_area of all PHYs in chiplet \"%s\" is larger than 1.0, which is not allowed."
			args = (chiplet_name, )
			print_validation_error(msg, args)
			errors += 1
		# The fraction_power_bumps parameter bust be between 0.0 and 1.0
		if chiplet["fraction_power_bumps"] < 0.0 or chiplet["fraction_power_bumps"] > 1.0:
			msg = "Invalid fraction_power_bumps \"%.3f\" of chiplet \"%s\", this parameter must be between 0.0 and 1.0."
			args = (chiplet["fraction_power_bumps"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
		# Technology node must be present in technology nodes file
		if chiplet["technology"] not in technology:
			msg = "The technology \"%s\" used in chiplet \"%s\" has not been specified in the technology file"
			args = (chiplet["technology"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
		# The power must be non-negative
		if chiplet["power"] < 0.0:
			msg = "Invalid power \"%.3f\" of chiplet \"%s\", this parameter must be non-negative."
			args = (chiplet["power"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
		# The internal latency must be positive
		if chiplet["internal_latency"] <= 0:
			msg = "Invalid internal latency \"%.3f\" of chiplet \"%s\", this parameter must be positive."
			msg += " If not used, set to NaN."
			args = (chiplet["internal_latency"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
		# The unit count must be an integer and at least 1
		if chiplet["unit_count"] % 1 != 0:
			msg = "Invalid unit count \"%s\" of chiplet \"%s\", this parameter must be an integer."
			args = (chiplet["unit_count"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
		# The unit count must be at least 1
		if chiplet["unit_count"] < 1:
			msg = "Invalid unit count \"%s\" of chiplet \"%s\", this parameter must be at least 1."
			args = (chiplet["unit_count"], chiplet_name)
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")


def validate_packaging(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["packaging", "technologies"]
	hlp.read_required_inputs(inputs, required_inputs)
	packaging = inputs["packaging"]
	technologies = inputs["technologies"]
	print("Validating packaging...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Link routing must be manhattan or eucledian
	if packaging["link_routing"] not in ["manhattan", "euclidean"]:
		msg = "Invalid link routing \"%s\", only \"manhattan\" and \"euclidean\" are allowed."
		args = (packaging["link_routing"], )
		print_validation_error(msg, args)
		errors += 1
	# link_latency_type must be constant or function
	if packaging["link_latency_type"] not in ["constant", "function"]:
		msg = "Invalid link latency type \"%s\", only \"constant\" and \"function\" are allowed."
		args = (packaging["link_latency_type"], )
		print_validation_error(msg, args)
		errors += 1
	# If the link_latency_type is function, the function must be valid
	if packaging["link_latency_type"] == "function":
		try:
			tmp = int(math.ceil(eval(packaging["link_latency"])(3)))
		except:
			msg = "Invalid link latency function \"%s\". Unable to evaluate function."
			args = (packaging["link_latency"], )
			print_validation_error(msg, args)
			errors += 1
	# link_power_type must be constant or function
	if packaging["link_power_type"] not in ["constant", "function"]:
		msg = "Invalid link power type \"%s\", only \"constant\" and \"function\" are allowed."
		args = (packaging["link_power_type"], )
		print_validation_error(msg, args)
		errors += 1
	# If the link_power_type is function, the function must be valid
	if packaging["link_power_type"] == "function":
		try:	
			tmp = int(math.ceil(eval(packaging["link_power"])(3)))
		except:
			msg = "Invalid link power function \"%s\". Unable to evaluate function."
			args = (packaging["link_power"], )
			print_validation_error(msg, args)
			errors += 1
	# The packaging yield must be between 0.0 and 1.0
	if packaging["packaging_yield"] < 0.0 or packaging["packaging_yield"] > 1.0:
		msg = "Invalid packaging yield \"%s\". This parameter must be between 0.0 and 1.0."
		args = (packaging["packaging_yield"], )
		print_validation_error(msg, args)
		errors += 1
	# Check that active interposers contain the required information
	if packaging["is_active"]:
		# Validate interposer-router latency: Must be present and non-negative
		if "latency_irouter" not in packaging:
			msg = "Active interposers must specify the parameter \"latency_iroute\""
			print_validation_error(msg, args)
			errors += 1
		elif packaging["latency_irouter"] < 0:
			msg = "Invalid interposer-router latency \"%s\". This parameter must not be negative."
			args = (packaging["latency_irouter"], )
			print_validation_error(msg, args)
			errors += 1
		# Validate interposer-router power consumption: Must be present and non-negative
		if "power_irouter" not in packaging:
			msg = "Active interposers must specify the parameter \"power_irouter\""
			print_validation_error(msg, args)
			errors += 1
		elif packaging["power_irouter"] < 0:
			msg = "Invalid interposer-router power consumption \"%s\". This parameter must not be negative."
			args = (packaging["power_irouter"], )
			print_validation_error(msg, args)
			errors += 1	
	# Check that interposers contain the required information
	if packaging["has_interposer"]:
		if "interposer_technology" not in packaging:
			msg = "Packages with interposers must specify the parameter \"interposer_technology\""
			print_validation_error(msg, args)
			errors += 1
		elif packaging["interposer_technology"] not in technologies:
			msg = "Interposer Technology \"%s\" not found in technology-file."
			args = (packaging["interposer_technology"], )
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")
	

def validate_placement(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["placement", "chiplets"]
	hlp.read_required_inputs(inputs, required_inputs)
	placement = inputs["placement"]
	chiplets = inputs["chiplets"]
	print("Validating placement...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Iterate over all chiplets to check for overlapping
	for (cid1, cdesc1) in enumerate(placement["chiplets"]):
		chiplet_1 = chiplets[cdesc1["name"]]
		# Rotate the chiplet if needed
		chiplet_1 = hlp.rotate_chiplet(chiplet_1, cdesc1["rotation"])
		# Extract info
		(x1,y1) = (cdesc1["position"]["x"], cdesc1["position"]["y"])				# x and y position
		(w1,h1) = (chiplet_1["dimensions"]["x"], chiplet_1["dimensions"]["y"])		# with and height	
		(l1,r1,t1,b1) = (x1, x1 + w1, y1, y1 + h1)									# left, right, top, bottom
		# Iterate over all other chiplets
		for cid2 in range(cid1+1, len(placement["chiplets"])):
			cdesc2 = placement["chiplets"][cid2]
			chiplet_2 = chiplets[cdesc2["name"]]
			# Rotate the chiplet if needed
			chiplet_2 = hlp.rotate_chiplet(chiplet_2, cdesc2["rotation"])
			# Extract info
			(x2,y2) = (cdesc2["position"]["x"], cdesc2["position"]["y"])			# x and y position
			(w2,h2) = (chiplet_2["dimensions"]["x"], chiplet_2["dimensions"]["y"])	# with and height
			(l2,r2,t2,b2) = (x2, x2 + w2, y2, y2 + h2)								# left, right, top, bottom
			# Check for overlap
			if not ((r1 <= l2) or (r2 <= l1) or (t1 <= b2) or (t2 <= b1)):
				msg = "Chiplets %d and %d are overlapping"
				args = (cid1, cid2)
				print_validation_error(msg, args)
				errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")



def validate_routing_table(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["chiplets", "placement", "routing_table", "topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	routing_table_ = inputs["routing_table"]
	routing_table_type = routing_table_["type"]
	routing_table = routing_table_["table"]
	topology = inputs["topology"]
	print("Validating routing table...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Check that all chiplets contain a next-hop entry for all possible destinations	
	for (cid1, cdesc1) in enumerate(placement["chiplets"]):
		# Check that the chiplet contains a routing table entry
		if ("chiplet", cid1) not in routing_table:
			msg = "Chiplet %d does not contain a routing table entry."
			args = (cid1, )
			print_validation_error(msg, args)
			errors += 1
		else:
			# Check that the routing table entry contains all possible destinations
			for (cid2, cdesc2) in enumerate(placement["chiplets"]):
				if cid1 != cid2 and ("chiplet", cid2) not in routing_table[("chiplet", cid1)]:
					msg = "Chiplet %d does not contain a routing table entry for destination chiplet %d."
					args = (cid1, cid2)
					print_validation_error(msg, args)
					errors += 1
	# Check that all interposer routers contain a next-hop entry for all possible destinations
	for (rid, irouter) in enumerate(placement["interposer_routers"]):
		# Check that the interposer router contains a routing table entry
		if ("irouter", rid) not in routing_table:
			msg = "Interposer router %d does not contain a routing table entry."
			args = (rid, )
			print_validation_error(msg, args)
			errors += 1
		else:
			# Check that the routing table entry contains all possible destinations
			for (cid, cdesc) in enumerate(placement["chiplets"]):
				if ("chiplet", cid) not in routing_table[("irouter", rid)]:
					msg = "Interposer router %d does not contain a routing table entry for destination chiplet %d."
					args = (rid, cid)
					print_validation_error(msg, args)
					errors += 1
	# Check that the routing table does not contain entries that are not valid
	max_chiplet_id = len(placement["chiplets"]) - 1
	max_irouter_id = len(placement["interposer_routers"]) - 1
	for node1 in routing_table:
		# Check that the source node is valid
		if node1[0] == "chiplet" and node1[1] > max_chiplet_id:
			msg = "Routing table contains an invalid source chiplet id %d."
			args = (node1[1], )
			print_validation_error(msg, args)
			errors += 1
		elif node1[0] == "irouter" and node1[1] > max_irouter_id:
			msg = "Routing table contains an invalid source interposer router id %d."
			args = (node1[1], )
			print_validation_error(msg, args)
			errors += 1
		# Check that the destination node is valid
		for node2 in routing_table[node1]:
			if node2[0] == "chiplet" and node2[1] > max_chiplet_id:
				msg = "Routing table contains an invalid destination chiplet id %d."
				args = (node2[1], )
				print_validation_error(msg, args)
				errors += 1
			elif node2[0] == "irouter" and node2[1] > max_irouter_id:
				msg = "Routing table contains an invalid destination interposer router id %d."
				args = (node2[1], )
				print_validation_error(msg, args)
				errors += 1
			# Do the following checks only if the source and destination are different
			if node1 != node2:
				# Check that the next-hop entry is valid	
				if routing_table_type == "default":
					possible_next_nodes = [routing_table[node1][node2]]
				elif routing_table_type == "extended":
					possible_next_nodes = [routing_table[node1][node2][prev] for prev in routing_table[node1][node2]]
				else:
					print("ERROR: Invalid routing table type \"%s\"." % routing_table_type)
					sys.exit(1)
				for node3 in possible_next_nodes:
					if node3[0] == "chiplet" and node3[1] > max_chiplet_id:
						msg = "Routing table contains an invalid next-hop chiplet id %d."
						args = (node3[1], )
						print_validation_error(msg, args)
						errors += 1
					elif node3[0] == "irouter" and node3[1] > max_irouter_id:
						msg = "Routing table contains an invalid next-hop interposer router id %d."
						args = (node3[1], )
						print_validation_error(msg, args)
						errors += 1
					# Check that the link is present in the topology
					cand_links = [l for l in topology if (l["ep1"]["type"] == node1[0] and l["ep1"]["outer_id"] == node1[1] and \
														  l["ep2"]["type"] == node3[0] and l["ep2"]["outer_id"] == node3[1]) or \
														 (l["ep1"]["type"] == node3[0] and l["ep1"]["outer_id"] == node3[1] and \
														  l["ep2"]["type"] == node1[0] and l["ep2"]["outer_id"] == node1[1])]
					if len(cand_links) == 0:
						msg = "Routing table contains a next-hop entry for a link that is not present in the topology."
						msg += "Link: %s -> %s"
						print_validation_error(msg, (node1, node3))
						errors += 1
					elif len(cand_links) > 1:
						msg = "Routing table contains a next-hop entry for a link that is present multiple times in the topology."
						msg += "Link: %s -> %s"
						print_validation_error(msg, (node1, node3))
						errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")


def validate_technologies(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["technologies"]
	hlp.read_required_inputs(inputs, required_inputs)
	technologies = inputs["technologies"]
	print("Validating technologies...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Iterate over all technologies
	for (tech_name, tech) in technologies.items():	
		# The PHY latency must be positive
		if tech["phy_latency"] <= 0:
			msg = "Invalid PHY latency \"%s\" of technology \"%s\", this parameter must be positive."
			args = (tech["phy_latency"], tech_name)
			print_validation_error(msg, args)
			errors += 1
		# The wafer radius must be positive
		if tech["wafer_radius"] <= 0:
			msg = "Invalid wafer radius \"%s\" of technology \"%s\", this parameter must be positive."
			args = (tech["wafer_radius"], tech_name)
			print_validation_error(msg, args)
			errors += 1
		# The wafer cost must be non-negative
		if tech["wafer_cost"] < 0:
			msg = "Invalid wafer cost \"%s\" of technology \"%s\", this parameter must be non-negative."
			args = (tech["wafer_cost"], tech_name)
			print_validation_error(msg, args)
			errors += 1
		# The defect density needs to be between 0.0 and 1.0
		if tech["defect_density"] < 0.0 or tech["defect_density"] > 1.0:
			msg = "Invalid defect density \"%s\" of technology \"%s\", this parameter must be between 0.0 and 1.0."
			args = (tech["defect_density"], tech_name)
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")


def validate_topology(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["chiplets", "placement", "topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	topology = inputs["topology"]
	print("Validating topology...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Check that only valid chiplets/phys or interposer-routers/ports are referenced and that each port is referenced only once
	used_phys = []
	used_ports = []
	max_chiplet_id = len(placement["chiplets"]) - 1
	max_irouter_id = len(placement["interposer_routers"]) - 1
	for (lid, link) in enumerate(topology):
		endpoints = [link["ep1"],link["ep2"]]
		for ep in endpoints:
			if ep["type"] not in ["chiplet","irouter"]:
				msg = "Invalid link-endpoint type \"%s\" for link %d. The endpoint type must be \"chiplet\" or \"irouter\"."
				args = (ep["type"], lid)
				print_validation_error(msg, args)
				errors += 1
			# For endpoints that are chiplets 
			elif ep["type"] == "chiplet":
				max_phy_id = len(chiplets[placement["chiplets"][ep["outer_id"]]["name"]]["phys"]) - 1
				# Check that the chiplet-id is valid
				if ep["outer_id"] > max_chiplet_id:
					msg = "Invalid chiplet-id \"%s\" for link %d. The maximum chiplet-id is %d."
					args = (ep["outer_id"], lid, max_chiplet_id)
					print_validation_error(msg, args)
					errors += 1
				# Check if PHY-id is valid
				elif ep["inner_id"] > max_phy_id:
					msg = "Invalid PHY-id \"%s\" for link %d. The maximum PHY-id for chiplet %d is %d."
					args = (ep["inner_id"], lid, ep["outer_id"], max_phy_id)
					print_validation_error(msg, args)
					errors += 1
				# Check that each PHY is only used once
				elif (ep["outer_id"],ep["inner_id"]) in used_phys:
					msg = "The PHY number %s of the chiplet with id %s is used multiple times."
					args = (ep["inner_id"], ep["outer_id"])
					print_validation_error(msg, args)
					errors += 1
				# Remember that this PHY has been used
				else:
					used_phys.append((ep["outer_id"],ep["inner_id"]))	
			# For endpoints that are interposer routers
			elif ep["type"] == "irouter":
				max_port_id = placement["interposer_routers"][ep["outer_id"]]["ports"] - 1
				# Check that the interposer-router-id is valid
				if ep["outer_id"] > max_irouter_id:
					msg = "Invalid interposer-router-id \"%s\" for link %d. The maximum interposer-router-id is %d."
					args = (ep["outer_id"], lid, max_irouter_id)
					print_validation_error(msg, args)
					errors += 1
				# Check that the port-id is valid
				elif ep["inner_id"] > max_port_id:
					msg = "Invalid port-id \"%s\" for link %d. The maximum port-id for interposer-router %d is %d."
					args = (ep["inner_id"], lid, ep["outer_id"], max_port_id)
					print_validation_error(msg, args)
					errors += 1
				# Check that each port is only used once
				elif (ep["outer_id"],ep["inner_id"]) in used_ports:
					msg = "The port number %s of the interposer-router with id %s is used multiple times."
					args = (ep["inner_id"], ep["outer_id"])
					print_validation_error(msg, args)
					errors += 1
				# Remember that this port has been used
				else:
					used_ports.append((ep["outer_id"],ep["inner_id"]))
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")


def validate_traffic_by_unit(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["chiplets","placement","traffic_by_unit"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	traffic_by_unit = inputs["traffic_by_unit"]
	print("Validating traffic by unit...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Check that all source and destination chiplets are valid
	max_chiplet_id = len(placement["chiplets"]) - 1
	for ((scid,suid),(dcid,duid)) in traffic_by_unit:
		if scid > max_chiplet_id:
			msg = "Invalid source chiplet id %d."
			args = (sid, )
			print_validation_error(msg, args)
			errors += 1
		if suid > chiplets[placement["chiplets"][scid]["name"]]["unit_count"] - 1:
			msg = "Invalid source unit id %d in chiplet %d."
			args = (suid, scid)
			print_validation_error(msg, args)
			errors += 1
		if dcid > max_chiplet_id:
			msg = "Invalid destination chiplet id %d."
			args = (did, )
			print_validation_error(msg, args)
			errors += 1
		if duid > chiplets[placement["chiplets"][dcid]["name"]]["unit_count"] - 1:
			msg = "Invalid destination unit id %d in chiplet %d."
			args = (duid, dcid)
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")

def validate_traffic_by_chiplet(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["placement","traffic_by_chiplet"]
	hlp.read_required_inputs(inputs, required_inputs)
	placement = inputs["placement"]
	traffic_by_chiplet = inputs["traffic_by_chiplet"]
	print("Validating traffic by chiplet...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Check that all source and destination chiplets are valid
	max_chiplet_id = len(placement["chiplets"]) - 1
	for (scid,dcid) in traffic_by_chiplet:
		if scid > max_chiplet_id:
			msg = "Invalid source chiplet id %d."
			args = (sid, )
			print_validation_error(msg, args)
			errors += 1
		if dcid > max_chiplet_id:
			msg = "Invalid destination chiplet id %d."
			args = (did, )
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")




# TODO: The BookSim configuration is only partially validated.
def validate_booksim_config(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["booksim_config"]
	hlp.read_required_inputs(inputs, required_inputs)
	booksim_config = inputs["booksim_config"]
	print("Validating Booksim configuration...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	# Check that the mode is either traffic or trace
	if booksim_config["mode"] not in ["traffic", "trace"]:
		msg = "Invalid mode \"%s\" in booksim_config. Only \"traffic\" and \"trace\" are allowed."
		args = (booksim_config["mode"], )
		print_validation_error(msg, args)
		errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")

def validate_trace(inputs):
	if not inputs["validate"]:
		return
	# Read the required inputs
	required_inputs = ["chiplets", "placement", "trace"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	trace = inputs["trace"]
	print("Validating trace...", end = "") if inputs["verbose"] else None
	# Count the number of errors
	errors = 0
	for packet in trace:
		# Check that the source chiplets are valid
		if packet["source_chiplet"] >= len(placement["chiplets"]) or packet["source_chiplet"] < 0:
			msg = "Invalid source chiplet id %d in trace. The maximum chiplet id is %d."
			args = (packet["source_chiplet"], )
			print_validation_error(msg, args)
			errors += 1
		# Check that the destination unit is valid
		if packet["destination_chiplet"] >= len(placement["chiplets"]) or packet["destination_chiplet"] < 0:
			msg = "Invalid destination chiplet id %d in trace. The maximum chiplet id is %d."
			args = (packet["destination_chiplet"], )
			print_validation_error(msg, args)
			errors += 1
		# Check that the source unit is valid
		if packet["source_unit"] >= chiplets[placement["chiplets"][packet["source_chiplet"]]["name"]]["unit_count"] or packet["source_unit"] < 0:
			msg = "Invalid source unit id %d in trace. The maximum unit id is %d."
			args = (packet["source_unit"], )
			print_validation_error(msg, args)
			errors += 1
		# Check that the destination unit is valid
		if packet["destination_unit"] >= chiplets[placement["chiplets"][packet["destination_chiplet"]]["name"]]["unit_count"] or packet["destination_unit"] < 0:
			msg = "Invalid destination unit id %d in trace. The maximum unit id is %d."
			args = (packet["destination_unit"], )
			print_validation_error(msg, args)
			errors += 1
	# Check that the reverse dependencies are valid
	valid_packet_ids = sorted([packet["id"] for packet in trace])
	all_rev_dep_ids = sorted(list(set([rev_dep for packet in trace for rev_dep in packet["reverse_dependencies"]])))
	val_ptr = 0
	for rev_ptr in range(len(all_rev_dep_ids)):
		while valid_packet_ids[val_ptr] < all_rev_dep_ids[rev_ptr]:
			val_ptr += 1
		if valid_packet_ids[val_ptr] != all_rev_dep_ids[rev_ptr]:
			msg = "Invalid reverse dependency %d in trace. No packet with this id exists."
			args = (all_rev_dep_ids[rev_ptr], )
			print_validation_error(msg, args)
			errors += 1
	# Print validation result
	print(" completed with %d errors." % errors) if inputs["verbose"] else None
	if errors > 0:
		print("Note that RapidChiplet might produce incorrect results or crash when running with invalid inputs.")
	
		
validation_functions = {
	"chiplets": validate_chiplets,
	"packaging": validate_packaging,
	"placement": validate_placement,
	"routing_table": validate_routing_table,
	"technologies": validate_technologies,
	"topology": validate_topology,
	"traffic_by_unit": validate_traffic_by_unit,
	"traffic_by_chiplet": validate_traffic_by_chiplet,
	"trace": validate_trace,
	"booksim_config": validate_booksim_config,
}
