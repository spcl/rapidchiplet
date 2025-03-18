# Import python libraries
import sys
import copy
import math
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as ptch

# Import RapidChiplet files
import global_config as cfg
import helpers as hlp

# Visualize a single chiplet
def visualize_design(inputs, design_name, show_chiplet_id = False, show_phy_id = False):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","placement","topology"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	topology = inputs["topology"]
	# Initialize the plot
	fix, ax = plt.subplots()	
	plt.axis("off")
	plt.axis('equal')
	(maxx, maxy) = (0,0)
	phylocs = {}
	# Iterate through chiplets
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		pos = (chiplet_desc["position"]["x"], chiplet_desc["position"]["y"])
		# Rotate the chiplet if needed
		chiplet = hlp.rotate_chiplet(chiplet, chiplet_desc["rotation"])
		# Draw the chiplet
		col = cfg.chiplet_colors[chiplet["type"]] if chiplet["type"] in cfg.chiplet_colors else "#CCCCCC"
		ax.add_patch(ptch.Rectangle(pos, chiplet["dimensions"]["x"], chiplet["dimensions"]["y"], edgecolor = "#000000", facecolor = col))
		if show_chiplet_id:
			ax.text(pos[0] + chiplet["dimensions"]["x"] / 2, pos[1] + chiplet["dimensions"]["y"] / 2, str(cid), ha = "center", va = "center", fontsize = 12, fontweight = "bold")
		# Update the canvas size
		maxx = max(maxx, pos[0] + chiplet["dimensions"]["x"])
		maxy = max(maxy, pos[1] + chiplet["dimensions"]["y"])
		# Iterate through the chiplet's phys
		radius = 0.3
		for (pid, phy) in enumerate(chiplet["phys"]):
			# Draw PHY
			ax.add_patch(ptch.Circle((pos[0] + phy["x"], pos[1] + phy["y"]), radius = radius, edgecolor = "#000000", facecolor = "none"))
			if show_phy_id:
				ax.text(pos[0] + phy["x"], pos[1] + phy["y"], str(pid), ha = "center", va = "center", fontsize = 6)
			# Store PHY location (needed to draw links)
			phylocs[(cid, pid)] = (pos[0] + phy["x"], pos[1] + phy["y"])
	# Iterate trough interposer-routers
	for (rid, irouter) in enumerate(placement["interposer_routers"]):
		# Draw interposer-routers
		ax.add_patch(ptch.Rectangle((irouter["position"]["x"]-0.5, irouter["position"]["y"]-0.5), 1, 1, linewidth = 0, facecolor = "#990000", zorder = 10))
	# Iterate through links
	for link in topology:
		ep1 = (link["ep1"]["outer_id"], link["ep1"]["inner_id"])
		ep2 = (link["ep2"]["outer_id"], link["ep2"]["inner_id"])
		# Draw link
		(x1,y1) = phylocs[ep1] if link["ep1"]["type"] == "chiplet" else (placement["interposer_routers"][ep1[0]]["position"]["x"],placement["interposer_routers"][ep1[0]]["position"]["y"])
		(x2,y2) = phylocs[ep2] if link["ep2"]["type"] == "chiplet" else (placement["interposer_routers"][ep2[0]]["position"]["x"],placement["interposer_routers"][ep2[0]]["position"]["y"])
		# Center of circle
		af = link["arc_factor"] if "arc_factor" in link else 3.0
		xdir, ydir = x2-x1, y2-y1
		ndir = np.sqrt(xdir**2 + ydir**2)
		vx, vy = (-ydir / ndir, xdir / ndir)
		xx, yy = ((x1 + x2) / 2) + af * ndir * vx, ((y1 + y2) / 2) + af * ndir * vy
		# Parameters for the circular arc
		radius = np.sqrt((x1 - xx)**2 + (y1 - yy)**2)  # Radius of the circle
		angle_start = np.arctan2(y1 - yy, x1 - xx)
		angle_end = np.arctan2(y2 - yy, x2 - xx)
		if angle_end < angle_start:
			angle_end += 2 * np.pi
		# Define the arc
		theta = np.linspace(angle_start, angle_end, 100)
		x_arc = xx + radius * np.cos(theta)
		y_arc = yy + radius * np.sin(theta)
		# Plot the arc
		col = link["color"] if "color" in link else cfg.link_color
		ax.plot(x_arc, y_arc, lw=2.0, color = col)
	# Store image
	plt.savefig("images/%s.pdf" % design_name)

# Visualize a single chiplet
def visualize_chiplet(chiplet, chiplet_name):
	# Initialize the plot
	fix, ax = plt.subplots()	
	ax.set_xlim(0,chiplet["dimensions"]["x"]) 
	ax.set_ylim(0,chiplet["dimensions"]["y"]) 
	plt.axis("off")
	plt.axis('equal')
	# Plot chiplet
	col = cfg.chiplet_colors[chiplet["type"]] if chiplet["type"] in cfg.chiplet_colors else "#CCCCCC"
	ax.add_patch(ptch.Rectangle((0,0), chiplet["dimensions"]["x"], chiplet["dimensions"]["y"], edgecolor = "#000000", facecolor = col))
	# Plot PHYs
	radius = max(chiplet["dimensions"]["x"], chiplet["dimensions"]["y"]) / 25
	fontsize = min(chiplet["dimensions"]["x"], chiplet["dimensions"]["y"]) * 2
	for (pid, phy) in enumerate(chiplet["phys"]):
		ax.add_patch(ptch.Circle((phy["x"], phy["y"]), radius = radius, edgecolor = "#000000", facecolor = "#000000"))
		ax.text(phy["x"], phy["y"], str(pid), ha = "center", va = "center", color = "#FFFFFF", fontsize = fontsize)
	plt.savefig("images/%s.pdf" % chiplet_name)

def visualize_routing_tables(routing_table_type, routing_table):
	for cur in routing_table:
		print("=" * 90)
		print("Routing table for %s %d" % cur)
		print("=" * 90)
		for dst in routing_table[cur]:
			print("Destination %s %d" % dst, end = " ")
			if routing_table_type == "default":
				if routing_table[cur][dst] == None:
					if cur == dst:
						print(" => local")
					else:
						print(" => no route")
				else:
					print(" => next hop %s %d" % routing_table[cur][dst])
			elif routing_table_type == "extended":
				print()
				for prev in routing_table[cur][dst]:
					if prev == "-1":
						print("  Previous local", end = " ")
					else:
						print("  Previous %s %d" % prev, end = " ")
					if routing_table[cur][dst][prev] == None:
						if cur == dst:
							print(" => local")
						else:
							print(" => no route")
					else:
						print(" => next hop %s %d" % routing_table[cur][dst][prev])
			else:
				print("ERROR: Unknown routing table type \"%s\"." % routing_table_type)
	
if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()	
	parser.add_argument("-df", "--design_file", required = False, help = "Path to the \"design\" input file") 
	parser.add_argument("-cf", "--chiplet_file", required = False, help = "Path to the \"chiplets\" input file") 
	parser.add_argument("-cn", "--chiplet_name", required = False, help = "Name of the chiplet to visualize") 
	parser.add_argument("-rtf", "--routing_table_file", required = False, help = "Path to the \"routing_table\" input file")
	parser.add_argument("-sci", "--show_chiplet_id", required = False, action = "store_true", help = "Show chiplet IDs")
	parser.add_argument("-spi", "--show_phy_id", required = False, action = "store_true", help = "Show PHY IDs")
	args = parser.parse_args()
	# Check if the design_file argument was provided
	if args.design_file != None:
		# Read the design file
		design = hlp.read_json(filename = args.design_file)
		inputs = {"design":design,"verbose":True,"validate":True}
		design_name = args.design_file.split("/")[-1].split(".")[0]
		# Visualize the design
		visualize_design(inputs, design_name, show_chiplet_id = args.show_chiplet_id, show_phy_id = args.show_phy_id)
	elif args.chiplet_file != None and args.chiplet_name != None:
		# Read the chiplet file
		chiplets = hlp.read_json(filename = args.chiplet_file)
		# Visualize the chiplet
		if args.chiplet_name in chiplets:
			visualize_chiplet(chiplets[args.chiplet_name], args.chiplet_name)
		else:
			print("error: The chiplet \"%s\" was not found in the chiplet file \"%s\"." % (args.chiplet_name, args.chiplet_file))
			sys.exit()
	elif args.routing_table_file != None:
		# Read the routing table file
		routing_table_ = hlp.read_json(filename = args.routing_table_file)
		routing_table_type = routing_table_["type"]
		routing_table = routing_table_["table"]
		# Visualize the routing tables
		visualize_routing_tables(routing_table_type, routing_table)
	else:
		print("error: Either the \"design_file\" or the \"chiplet_file\" and \"chiplet_name\" arguments must be provided.")
		sys.exit()	
