# Import python libraries
import sys
import math

# Generate a chiplet
# Currently supported PHY placements are: 4PHY_Corner, 4PHY_Edge, 6PHY_HM, 8PHY_OM, and xPHY_yPHY
def generate_chiplet(params, phy_placement):
	# Get the number of PHYs to compute the chiplet area
	phy_count_map = {"4PHY_Corner" : 4, "4PHY_Edge" : 4, "6PHY_HM" : 6, "8PHY_OM" : 8}
	# For PHY placements 4PHY_Corner, 4PHY_Edge, 6PHY_HM, and 8PHY_OM
	if phy_placement in phy_count_map:
		n_phys = phy_count_map[phy_placement]
	# For PHY placement "xPHY_yPHY"
	else:
		try:
			(x,y) = phy_placement.replace("PHY","").split("_")
			(x, y) = (int(x), int(y))
			n_phys = x + y
		except:
			print("Error: Invalid PHY placement \"%s\"" % phy_placement)
			sys.exit(1)
	# Compute the chiplet area 
	area = params["base_chiplet_area"] + n_phys * params["phy_area"]
	power = params["base_chiplet_power"] + n_phys * params["phy_power"]
	# Compute the PHY positions. We specify the center of the PHY with the bottom-left corner of the chiplet as origin
	phys = []
	a = math.sqrt(area)	# Side length of the square chiplet
	fp = params["fraction_power_bumps"]
	if phy_placement == "4PHY_Corner":
		p = math.sqrt(a**2 * (1 - fp)) / 4
		phys.append({"x" : p, "y" : p})					# South-west	ID 0
		phys.append({"x" : p, "y" : a-p})				# North-west	ID 1
		phys.append({"x" : a-p, "y" : a-p})				# North-east	ID 2
		phys.append({"x" : a-p, "y" : p})				# South-east	ID 3
	elif phy_placement == "4PHY_Edge":
		p = (a * (1 - math.sqrt(fp))) / 4
		phys.append({"x" : p, "y" : a/2})				# West  		ID 0
		phys.append({"x" : a/2, "y" : a-p})				# North  		ID 1
		phys.append({"x" : a-p, "y" : a/2})				# East 			ID 2
		phys.append({"x" : a/2, "y" : p})				# South 		ID 3
	elif phy_placement == "6PHY_HM":
		p1 = (a * (1 - fp)) / 6
		p2 = (a * (1 - fp)) / (4 + 8 * fp)
		phys.append({"x" : p2, "y" : a/2})				# West			ID 0
		phys.append({"x" : a/4, "y" : a-p1})			# North-west	ID 1
		phys.append({"x" : 3*a/4, "y" : a-p1})			# North-east	ID 2
		phys.append({"x" : a - p2, "y" : a/2})			# East			ID 3
		phys.append({"x" : 3*a/4, "y" : p1})			# South-east	ID 4
		phys.append({"x" : a/4, "y" : p1})				# South-west	ID 5
	elif phy_placement == "8PHY_OM":
		p1 = math.sqrt((a**2 * (1 - fp)) / 32)
		p2 = (a * (1 - fp)) / (16 - 8 * math.sqrt(2 - 2 * fp))
		phys.append({"x" : p1, "y" : p1})				# South-West	ID 0
		phys.append({"x" : p2, "y" : a/2})				# West			ID 1
		phys.append({"x" : p1, "y" : a-p1})				# North-West	ID 2
		phys.append({"x" : a/2, "y" : a-p2})			# North			ID 3
		phys.append({"x" : a-p1, "y" : a-p1})			# North-East	ID 4
		phys.append({"x" : a-p2, "y" : a/2})			# East			ID 5
		phys.append({"x" : a-p1, "y" : p1})				# South-East	ID 6
		phys.append({"x" : a/2, "y" : p2})				# South			ID 7
	# This must be the "xPHY_yPHY" case
	else:
		p1 = (a * x * (1-fp)) / (2 * (x + y))
		p2 = (a * y * (1-fp)) / (2 * y + 2 * x * fp)
		r = a - 2 * p1
		# South (IDs 0 to x-1)
		for i in range(x):
			phys.append({"x" : a / (2 * x) + i * (a / x), "y" : p1})	
		# East (IDs x to x+y-1)
		for i in range(y):
			phys.append({"x" : a - p2, "y" : 2 * p1 + r / (2 * y) + i * (r / y)})	
	# Add the fraction of bumps used by each phy
	for phy in phys:
		phy["fraction_bump_area"] = 1.0 / len(phys)
	# Create the chiplet
	chiplet = {
		"dimensions" : {"x" : a, "y" : a},
		"type" : params["chiplet_type"],
		"phys" : phys,
		"fraction_power_bumps" : params["fraction_power_bumps"],
		"technology" : params["technology"],
		"power" : power,									
		"relay" : params["chiplets_can_relay"],
		"internal_latency" : params["internal_latency"],		
		"unit_count" : params["units_per_chiplet"],
		}
	# Return the chiplet
	return chiplet
