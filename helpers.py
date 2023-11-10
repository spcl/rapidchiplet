# Import python libraries
import math
import json
import copy

# Write a JSON file
def write_file(filename, content):
    file = open(filename, "w")
    file.write(json.dumps(content, indent=4))
    file.close()

# Read a JSON file
def read_file(filename):
    file = open(filename, "r")
    file_content = json.loads(file.read())
    file.close()
    return file_content

# Rotate a chiplet
def rotate_chiplet(chiplet, rotation):
	# If no rotation is needed, return chiplet as-is
	if rotation == 0:
		return chiplet
	# Rotate the chiplet if needed
	chiplet = copy.deepcopy(chiplet)	
	rot = rotation // 90
	alpha = math.pi / 2 * rot
	(cx, cy) = (chiplet["dimensions"]["x"] / 2, chiplet["dimensions"]["y"] / 2)
	# Fix dimensions 
	if rot % 2 == 1:
		chiplet["dimensions"] = {"x" : chiplet["dimensions"]["y"],"y" : chiplet["dimensions"]["x"]}
	(cxn, cyn) = (chiplet["dimensions"]["x"] / 2, chiplet["dimensions"]["y"] / 2)
	# Fix new PHY positions
	for (pid, phy) in enumerate(chiplet["phys"]):
		(x, y) = (phy["x"] - cx, phy["y"] - cy)
		(xr,yr) = (x * math.cos(alpha) - y * math.sin(alpha), x * math.sin(alpha) + y * math.cos(alpha))
		chiplet["phys"][pid] = {"x" : cxn + xr, "y" : cyn + yr}
	# Return a rotated copy of the chiplet
	return chiplet

