# Import python libraries
import sys
import copy
import math
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as ptch

# Import RapidChiplet files
import helpers as hlp
import validation as vld

# Chiplet colors
chiplet_colors = {"compute" : "#66aadd", "memory" : "#66ddaa", "io" : "#ddaa66"}

# Visualize a chip design
def visualize_design(design_name, design):
	# Read input files
	chiplets = hlp.read_file(filename = design["chiplets_file"])
	placement = hlp.read_file(filename = design["chiplet_placement_file"])
	topology = hlp.read_file(filename = design["ici_topology_file"])
	# Validate design
	if not vld.validate_design(design, chiplets = chiplets, placement = placement, topology = topology):
		print("warning: This design contains validation errors - the visualization might fail")
	# Initialize the plot
	fix, ax = plt.subplots()	
	plt.axis("off")
	plt.axis('equal')
	(maxx, maxy) = (0,1)
	phylocs = {}
	# Iterate through chiplets
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		chiplet = chiplets[chiplet_desc["name"]]
		pos = (chiplet_desc["position"]["x"], chiplet_desc["position"]["y"])
		# Rotate the chiplet if needed
		chiplet = hlp.rotate_chiplet(chiplet, chiplet_desc["rotation"])
		# Draw the chiplet
		ax.add_patch(ptch.Rectangle(pos, chiplet["dimensions"]["x"], chiplet["dimensions"]["y"], edgecolor = "#000000", facecolor = chiplet_colors[chiplet["type"]] + "CC"))
		ax.text(pos[0] + chiplet["dimensions"]["x"] / 2, pos[1] + chiplet["dimensions"]["y"] / 2, str(cid), ha = "center", va = "center", fontsize = 6)
		# Update the canvas size
		maxx = max(maxx, pos[0] + chiplet["dimensions"]["x"])
		maxy = max(maxy, pos[1] + chiplet["dimensions"]["y"])
		# Iterate through the chiplet's phys
		radius = max(chiplet["dimensions"]["x"], chiplet["dimensions"]["y"]) / 15
		for (pid, phy) in enumerate(chiplet["phys"]):
			# Draw PHY
			ax.add_patch(ptch.Circle((pos[0] + phy["x"], pos[1] + phy["y"]), radius = radius, edgecolor = "#000000", facecolor = "#666666"))
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
		xx = (x1+x2)/2
		yy = (y1+y2)/2
		ax.arrow(xx,yy,(x2-x1)/2,(y2-y1)/2,zorder = 5, color = "#000000",length_includes_head=True, head_width = 0.75, head_length = 0.6, width = 0.3)
		ax.arrow(xx,yy,(x1-x2)/2,(y1-y2)/2,zorder = 5, color = "#000000",length_includes_head=True, head_width = 0.75, head_length = 0.6, width = 0.3)
	# Set canvas size
	ax.set_xlim(0,maxx) 
	ax.set_ylim(0,maxy) 
	# Store image
	plt.savefig("visualizations/design_%s.pdf" % design_name)

if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()	
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file") 
	args = parser.parse_args()
	# Read the design file
	design = hlp.read_file(filename = args.design_file)
	# Visualize the design
	visualize_design(design_name = args.design_file.split("/")[-1].split(".")[0], design = design)
	
