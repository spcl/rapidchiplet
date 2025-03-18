# Parameters:
# - rows: number of rows
# - cols: number of columns
# - chiplet_spacing: spacing between chiplets
def generate_grid_placement(params, chiplet, chiplet_name, use_memory = False):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	spacing = params["chiplet_spacing"]
	# Create the placement
	placement = []
	center_chiplet = chiplet_name
	border_chiplet = (chiplet_name + "_memory") if use_memory else chiplet_name
	# Add the chiplets
	for row in range(rows):
		for col in range(cols):
			x = col * (chiplet["dimensions"]["x"] + spacing)
			y = row * (chiplet["dimensions"]["y"] + spacing)
			full_chiplet_name = border_chiplet if col in [0, cols-1] else center_chiplet
			placement.append({"position" : {"x" : x, "y" : y}, "rotation" : 0, "name" : full_chiplet_name})
	# Return the placement
	return {"chiplets" : placement, "interposer_routers" : []}

# Parameters:
# - r: Radius of the hexagonal grid (see HexaMesh paper)
# - chiplet_spacing: spacing between chiplets
def generate_hexagonal_placement(params, chiplet, chiplet_name, use_memory = False):
	# Extract parameters
	r = params["radius"]		
	spacing = params["chiplet_spacing"]
	# Create the placement
	placement = []
	center_chiplet = chiplet_name
	border_chiplet = (chiplet_name + "_memory") if use_memory else chiplet_name
	# Add the chiplets
	rows = 2 * r + 1
	x_unit = chiplet["dimensions"]["x"] + spacing
	chiplets_per_row = list(range(r+1,2 * r+1,1)) + list(range(2 * r+1,r,-1))
	row_start_ids = [sum(chiplets_per_row[:i]) for i in range(len(chiplets_per_row))]
	row_start_x = [abs(i - (rows - 1) / 2) * x_unit / 2 for i in range(rows)] 
	for row in range(rows):
		for col in range(chiplets_per_row[row]):
			x = row_start_x[row] + col * x_unit
			y = row * (chiplet["dimensions"]["y"] + spacing)
			full_chiplet_name = border_chiplet if col in [0, chiplets_per_row[row]-1] else center_chiplet
			placement.append({"position" : {"x" : x, "y" : y}, "rotation" : 0, "name" : full_chiplet_name})
	# Return the placement
	return {"chiplets" : placement, "interposer_routers" : []}

placement_generation_functions = {
	"grid" : generate_grid_placement,
	"hexagonal" : generate_hexagonal_placement,
}
