# Import python libraries
import math

# Import RapidChiplet files
import global_config as cfg

###############################################################################
# Mesh Topology
###############################################################################

# The Mesh-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they are numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_mesh_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Generate links
	links = []
	for row in range(rows):
		for col in range(cols):
			# Horizontal links
			if col + 1 < cols:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row * cols + (col + 1), "inner_id" : 0}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
			# Vertical links
			if row + 1 < rows:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + col, "inner_id" : 3}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	

###############################################################################
# Torus Topology
###############################################################################o

# The Torus-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_torus_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Take Mesh-links as a starting point
	links = generate_mesh_topology(params)
	# Add horizontal wrap-around links
	for row in range(rows):
		ep1 = {"type" : "chiplet", "outer_id" : row * cols, "inner_id" : 0}
		ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols - 1, "inner_id" : 2}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
	# Add vertical wrap-around links
	for col in range(cols):
		ep1 = {"type" : "chiplet", "outer_id" : col, "inner_id" : 3}
		ep2 = {"type" : "chiplet", "outer_id" : (rows - 1) * cols + col, "inner_id" : 1}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	

###############################################################################
# FoldedTorus Topology
###############################################################################

# The FoldedTorus-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_folded_torus_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	links = []
	# Add horizontal links
	for row in range(rows):
		for col in range(-1,cols-1):
			(c1,c2,p1,p2) = (col+1, col+2, 0, 0) if col == -1 else ((col, col+1, 2, 2) if col == cols-2 else (col, col+2, 2,0))
			ep1 = {"type" : "chiplet", "outer_id" : row * cols + c1, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : row * cols + c2, "inner_id" : p2}
			(color, ep1, ep2) = (cfg.colors[1], ep1, ep2) if col % 2 == 0 else (cfg.colors[1], ep2, ep1)
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Add vertical links
	for col in range(cols):		
		for row in range(-1,rows-1):
			(r1,r2,p1,p2) = (row+1, row+2, 3, 3) if row == -1 else ((row, row+1, 1, 1) if row == rows-2 else (row, row+2, 1, 3))
			ep1 = {"type" : "chiplet", "outer_id" : r1 * cols + col, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : r2 * cols + col, "inner_id" : p2}
			(color, ep1, ep2) = (cfg.colors[2], ep1, ep2) if row % 2 == 0 else (cfg.colors[2], ep2, ep1)
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Return the links
	return links	

###############################################################################
# Flattened Butterfly Topology
###############################################################################

# The Falttened Butterfly topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_flattened_butterfly_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	n = rows * cols
	# Next phys-ID for horizontal and vertical links
	h_phy_id_map = [0 for i in range(n)]
	v_phy_id_map = [cols-1 for i in range(n)]
	# Generate the topology
	links = []
	for row in range(rows):
		for col in range(cols):
			# Horizontal
			for ocol in range(col+1, cols):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : h_phy_id_map[row * cols + col]}
				ep2 = {"type" : "chiplet", "outer_id" : row * cols + ocol, "inner_id" : h_phy_id_map[row * cols + ocol]}
				h_phy_id_map[row * cols + col] += 1
				h_phy_id_map[row * cols + ocol] += 1
				color = cfg.colors[abs(col - ocol) % len(cfg.colors)]
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Vertical
			for orow in range(row+1, rows):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : v_phy_id_map[row * cols + col]}
				ep2 = {"type" : "chiplet", "outer_id" : orow * cols + col, "inner_id" : v_phy_id_map[orow * cols + col]}
				v_phy_id_map[row * cols + col] += 1
				v_phy_id_map[orow * cols + col] += 1
				color = cfg.colors[abs(row - orow) % len(cfg.colors)]
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Return the links
	return links	

###############################################################################
# HexaMesh Topology
###############################################################################

# The HexaMesh topology is only applicable to a Hexagonal-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - r: radius
def generate_hexamesh_topology(params):
	# Extract parameters
	r = params["radius"]
	# Prepare auxiliary variables
	rows = 2 * r + 1
	chiplets_per_row = list(range(r+1,2 * r+1,1)) + list(range(2 * r+1,r,-1))
	row_start_ids = [sum(chiplets_per_row[:i]) for i in range(len(chiplets_per_row))]
	row_end_ids = [sum(chiplets_per_row[:i+1]) - 1 for i in range(len(chiplets_per_row))]
	# Generate the topology
	links = []
	for row in range(rows):
		for col in range(chiplets_per_row[row]):
			# Horizontal links
			if col < chiplets_per_row[row] - 1:
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 3}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col + 1, "inner_id" : 0}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3]})
			# Diagonal links of type '\'
			if (row < r) or (row >= r and row < rows -1 and col > 0):
				shift = 0 if row < r else -1
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 1] + col + shift, "inner_id" : 4}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
			# Diagonal links of type '/'
			if (row < r) or (row >= r and row < rows -1 and col < (chiplets_per_row[row] - 1)):
				shift = 1 if row < r else 0
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 1] + col + shift, "inner_id" : 5}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	

###############################################################################
# HexaTorus Topology
###############################################################################

# The HexaTorus topology is only applicable to a Hexagonal-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - r: radius
def generate_hexatorus_topology(params):
	# Extract parameters
	r = params["radius"]
	# Prepare auxiliary variables
	rows = 2 * r + 1
	chiplets_per_row = list(range(r+1,2 * r+1,1)) + list(range(2 * r+1,r,-1))
	row_start_ids = [sum(chiplets_per_row[:i]) for i in range(len(chiplets_per_row))]
	row_end_ids = [sum(chiplets_per_row[:i+1]) - 1 for i in range(len(chiplets_per_row))]
	# Use a HexaMesh as baseline
	links = generate_hexamesh_topology(params)
	# Add horizontal wrap-around links
	for row in range(rows):
		ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row], "inner_id" : 0}
		ep2 = {"type" : "chiplet", "outer_id" : row_end_ids[row], "inner_id" : 3}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[0]})
	# Add wrap-around links	of type '\'
	stride = 3 * r * (r + 1) - 2 * r
	step = r + 1
	for i in range(r, -1, -1):
		src1 = i
		dst1 = src1 + stride
		ep1 = {"type" : "chiplet", "outer_id" : src1, "inner_id" : 4}
		ep2 = {"type" : "chiplet", "outer_id" : dst1, "inner_id" : 1}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
		if i < r:
			src2 = row_start_ids[r-i+1] - 1
			dst2 = src2 + stride
			ep1 = {"type" : "chiplet", "outer_id" : src2, "inner_id" : 4}
			ep2 = {"type" : "chiplet", "outer_id" : dst2, "inner_id" : 1}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
		# Update stride and step
		stride -= step
		step += 1
	# Add wrap-around links	of type '/'
	stride = 3 * r * (r + 1)
	step = r + 2
	for i in range(r+1):
		src1 = i
		dst1 = src1 + stride
		ep1 = {"type" : "chiplet", "outer_id" : src1, "inner_id" : 5}
		ep2 = {"type" : "chiplet", "outer_id" : dst1, "inner_id" : 2}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
		if i > 0:
			src2 = row_start_ids[i]
			dst2 = src2 + stride
			ep1 = {"type" : "chiplet", "outer_id" : src2, "inner_id" : 5}
			ep2 = {"type" : "chiplet", "outer_id" : dst2, "inner_id" : 2}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
		# Update stride and step
		stride -= step
		step += 1
	# Return the links
	return links	

###############################################################################
# FoldedHexaTorus Topology
###############################################################################

# The HexaMesh topology is only applicable to a Hexagonal-placement
# Parameters: r
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
def generate_folded_hexatorus_topology(params):
	# Extract parameters
	r = params["radius"]
	# Prepare auxiliary variables
	rows = 2 * r + 1
	chiplets_per_row = list(range(r+1,2 * r+1,1)) + list(range(2 * r+1,r,-1))
	row_start_ids = [sum(chiplets_per_row[:i]) for i in range(len(chiplets_per_row))]
	row_end_ids = [sum(chiplets_per_row[:i+1]) - 1 for i in range(len(chiplets_per_row))]
	# Generate the topology
	links = []
	for row in range(rows):
		# Horizontal links	
		for col in range(-1, chiplets_per_row[row]-1):
			(c1,c2,p1,p2) = (col+1, col+2, 0, 0) if col == -1 else ((col, col+1, 3, 3) if col == chiplets_per_row[row]-2 else (col, col+2, 3, 0))
			ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + c1, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + c2, "inner_id" : p2}
			(color, ep1, ep2) = (cfg.colors[3], ep1, ep2) if col % 2 == 0 else (cfg.colors[3], ep2, ep1)
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
		# Add the remaining links
		for col in range(chiplets_per_row[row]):
			# Diagonal links of type '/'
			if (row < rows - 2) and ((col < chiplets_per_row[row] - 2) or (row + 2 <= r) or (row == r-1 and col == chiplets_per_row[row] - 2)):
				shift = 0 if row >= r else (1 if row == r-1 else 2)
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 2] + col + shift, "inner_id" : 5}
				(color, ep1, ep2) = (cfg.colors[2], ep1, ep2) if row % 2 == 0 else (cfg.colors[2], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '/' (top-right)
			if (row >= r) and ((col == chiplets_per_row[row] - 1) or (row == 2*r)):
				shift = -1 if row == r else 0
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row - 1] + col + shift, "inner_id" : 2}
				(color, ep1, ep2) = (cfg.colors[2], ep1, ep2) if row % 2 == 1 else (cfg.colors[2], ep2, ep1)
				links.append({"ep1" : ep2, "ep2" : ep1, "color" : color})
			# Diagonal Corner-case links of type '/' (bottom-left)
			if (row <= r) and ((col == 0) or (row == 0)):
				shift = 0 if row == r else 1
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 5}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 1] + col + shift, "inner_id" : 5}
				(color, ep1, ep2) = (cfg.colors[2], ep1, ep2) if row % 2 == 1 else (cfg.colors[2], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal links of type '\'
			if (row < rows - 2) and ((col > 1) or (row + 2 <= r) or (row == r-1 and col == 1)):
				shift = 0 if row + 2 <= r else (-1 if row == r-1 else -2)
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 2] + col + shift, "inner_id" : 4}
				(color, ep1, ep2) = (cfg.colors[1], ep1, ep2) if row % 2 == 0 else (cfg.colors[1], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '\' (top-left)
			if (row >= r) and ((col == 0) or (row == 2*r)):
				shift = 0 if row == r else 1
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row - 1] + col + shift, "inner_id" : 1}
				(color, ep1, ep2) = (cfg.colors[1], ep1, ep2) if row % 2 == 0 else (cfg.colors[1], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '\' (bottom-right)
			if (row <= r) and ((col == chiplets_per_row[row] - 1) or (row == 0)):
				shift = -1 if row == r else 0
				ep1 = {"type" : "chiplet", "outer_id" : row_start_ids[row] + col, "inner_id" : 4}
				ep2 = {"type" : "chiplet", "outer_id" : row_start_ids[row + 1] + col + shift, "inner_id" : 4}
				(color, ep1, ep2) = (cfg.colors[1], ep1, ep2) if row % 2 == 1 else (cfg.colors[1], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Return the links
	return links	

###############################################################################
# OctaMesh Topology
###############################################################################

# The OctaMesh-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_octamesh_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Use a 2D Mesh as baseline
	links = generate_mesh_topology(params)
	# Adjust the PHY-ids
	for link in links:
		for ep in [link["ep1"], link["ep2"]]:
			ep["inner_id"] = 1 + 2 * ep["inner_id"]
	# Add the diagonal links
	for row in range(rows):
		for col in range(cols):
			# Diagonal links of type '/'
			if row < rows - 1 and col < cols - 1:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 4}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + (col + 1), "inner_id" : 0}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3]})
			# Diagonal links of type '\'
			if row < rows - 1 and col > 0:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + (col - 1), "inner_id" : 6}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[4]})
	# Return the links
	return links	

###############################################################################
# OctaTorus Topology
###############################################################################

# The OctaMesh-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_octatorus_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Use a OctaMesh as baseline
	links = generate_octamesh_topology(params)
	# Add horizontal wrap-around links
	for row in range(rows):
		ep1 = {"type" : "chiplet", "outer_id" : row * cols, "inner_id" : 1}
		ep2 = {"type" : "chiplet", "outer_id" : row * cols + cols - 1, "inner_id" : 5}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[0]})
	# Add vertical wrap-around links
	for col in range(cols):
		ep1 = {"type" : "chiplet", "outer_id" : col, "inner_id" : 7}
		ep2 = {"type" : "chiplet", "outer_id" : (rows - 1) * cols + col, "inner_id" : 3}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[0]})
	# Add diagonal wrap-around links of type '/'
	ep1 = {"type" : "chiplet", "outer_id" : 0, "inner_id" : 0}
	ep2 = {"type" : "chiplet", "outer_id" : rows * cols - 1, "inner_id" : 4}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
	for i in range(1, max(rows, cols) - 1):
		for (row, col) in [(i,0), (0,i)]:
			src = (row, col)
			dst = (row, col)
			while dst[0] < rows - 1 and dst[1] < cols - 1:
				dst = (dst[0] + 1, dst[1] + 1)
			if (dst != src) and (max(src[0], dst[0]) < rows) and (max(src[1], dst[1]) < cols):
				ep1 = {"type" : "chiplet", "outer_id" : src[0] * cols + src[1], "inner_id" : 0}
				ep2 = {"type" : "chiplet", "outer_id" : dst[0] * cols + dst[1], "inner_id" : 4}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
	# Add diagonal wrap-around links of type '\'
	ep1 = {"type" : "chiplet", "outer_id" : cols - 1, "inner_id" : 6}
	ep2 = {"type" : "chiplet", "outer_id" : (rows - 1) * cols, "inner_id" : 2}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	for i in range(1, max(rows, cols) - 1):
		for (row, col) in [(i,cols-1), (0,i)]:
			src = (row, col)
			dst = (row, col)
			while dst[0] < rows - 1 and dst[1] > 0:
				dst = (dst[0] + 1, dst[1] - 1)
			if (dst != src) and (max(src[0], dst[0]) < rows) and (max(src[1], dst[1]) < cols):
				ep1 = {"type" : "chiplet", "outer_id" : src[0] * cols + src[1], "inner_id" : 6}
				ep2 = {"type" : "chiplet", "outer_id" : dst[0] * cols + dst[1], "inner_id" : 2}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	

###############################################################################
# FoldedOctaTorus Topology
###############################################################################

# The FoldedOctaTorus-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_folded_octatorus_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Generate topology
	links = []
	# Add horizontal links
	for row in range(rows):
		for col in range(-1, cols-1):
			(c1,c2,p1,p2) = (col+1, col+2, 1, 1) if col == -1 else ((col, col+1, 5, 5) if col == cols-2 else (col, col+2, 5, 1))
			ep1 = {"type" : "chiplet", "outer_id" : row * cols + c1, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : row  * cols + c2, "inner_id" : p2}
			(color, ep1, ep2) = (cfg.colors[1], ep1, ep2) if col % 2 == 0 else (cfg.colors[1], ep2, ep1)
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Add vertical links
	for col in range(cols):
		for row in range(-1, rows-1):
			(r1,r2,p1,p2) = (row+1, row+2, 7, 7) if row == -1 else ((row, row+1, 3, 3) if row == rows-2 else (row, row+2, 3, 7))
			ep1 = {"type" : "chiplet", "outer_id" : r1 * cols + col, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : r2 * cols + col, "inner_id" : p2}
			(color, ep1, ep2) = (cfg.colors[2], ep1, ep2) if row % 2 == 0 else (cfg.colors[2], ep2, ep1)
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Add diagonal links
	for row in range(rows):
		for col in range(cols):
			# Diagonal links of type '\'
			if row < rows - 2 and col > 1:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 2) * cols + (col - 2), "inner_id" : 6}
				(color, ep1, ep2) = (cfg.colors[4], ep1, ep2) if row % 2 == 0 else (cfg.colors[4], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '\' (top-left)
			if (row == rows - 1 or col == 0) and (row > 0 and col < cols - 1):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : (row - 1) * cols + (col + 1), "inner_id" : 2}
				(color, ep1, ep2) = (cfg.colors[4], ep2, ep1) if row % 2 == 1 else (cfg.colors[4], ep1, ep2)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '\' (bottom-right)
			if (row == 0 or col == cols - 1) and (row < rows - 1 and col > 0):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 6}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + (col - 1), "inner_id" : 6}
				(color, ep1, ep2) = (cfg.colors[4], ep1, ep2) if row % 2 == 1 else (cfg.colors[4], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal links of type '/'
			if row < rows - 2 and col < cols - 2:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 4}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 2) * cols + (col + 2), "inner_id" : 0}
				(color, ep1, ep2) = (cfg.colors[3], ep1, ep2) if row % 2 == 0 else (cfg.colors[3], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '/' (top-right)
			if (row == rows - 1 or col == cols - 1) and (row > 0 and col > 0):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 4}
				ep2 = {"type" : "chiplet", "outer_id" : (row - 1) * cols + (col - 1), "inner_id" : 4}
				(color, ep1, ep2) = (cfg.colors[3], ep2, ep1) if row % 2 == 1 else (cfg.colors[3], ep1, ep2)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
			# Diagonal Corner-case links of type '/' (bottom-left)
			if (row == 0 or col == 0) and (row < rows - 1 and col < cols - 1):
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 0}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + (col + 1), "inner_id" : 0}
				(color, ep1, ep2) = (cfg.colors[3], ep1, ep2) if row % 2 == 1 else (cfg.colors[3], ep2, ep1)
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
	# Return the links
	return links	

###############################################################################
# Hypercube Topology
###############################################################################

# The Hypercube-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_hypercube_topology(params):
	# Function to compute hamming distance
	def compute_hamming_distance(a, b):
		hdist = bin(a ^ b).count("1")
		abin, bbin = bin(a)[2:], bin(b)[2:]
		nbit = max(len(abin), len(bbin))
		abin, bbin = abin.zfill(nbit), bbin.zfill(nbit)
		diff = [i for i in range(1,nbit+1) if abin[-i] != bbin[-i]]
		return hdist, diff
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	N = rows * cols
	lrows = int(math.log2(rows))
	lcols = int(math.log2(cols))
	# Show next horizontal and vertical PHY-id
	hphy_map = [0 for i in range(N)]
	vphy_map = [lcols for i in range(N)]
	# Generate the topology
	links = []
	for src in range(N):
		for dst in range(src+1,N):
			hamming_distance, different_bits = compute_hamming_distance(src, dst)
			if hamming_distance == 1:
				phy_map = hphy_map if src // cols == dst // cols else vphy_map
				ep1 = {"type" : "chiplet", "outer_id" : src, "inner_id" : phy_map[src]}
				ep2 = {"type" : "chiplet", "outer_id" : dst, "inner_id" : phy_map[dst]}
				color = cfg.colors[different_bits[0] % len(cfg.colors)]
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : color})
				phy_map[src] += 1
				phy_map[dst] += 1
	# Return the links
	return links	

###############################################################################
# DoubleButterfly Topology 
###############################################################################

# The DoubleButterfly-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_double_butterfly_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Check that rows and columns are valid
	if math.log2(rows) % 1 != 0 or math.log2(cols) % 1 != 0 or rows != cols:
		print("Error: DoubleButterfly topology is only applicable if both the number of rows and columns are a power of 2 and they are equal")
		sys.exit(1)
	# Compute intermediate values
	N = rows * cols
	stages = int(math.log2(rows))
	links = []
	# Add the horizontal links
	for row in range(rows):
		(p1,p2) = (3, 0) if row < (rows//2) else (2, 1)
		for col in range(cols-1):
			ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : row * cols + (col + 1) % cols, "inner_id" : p2}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
	# Add the diagonal links
	for stage in range(stages):
		for scol in range(2**stage-1, cols, 2**(stage+1)):
			dcol = scol + 1
			for srow in range(rows):
				drow = ((srow // 2**(stage+1)) * 2**(stage+1)) + ((srow + 2**stage) % 2**(stage+1))
				p1 = 2 if srow < (rows//2) else 3
				p2 = 1 if drow < (rows//2) else 0
				ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p1}
				ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p2}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	

###############################################################################
# ButterDonut Topology 
###############################################################################

# The ButterDonut-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_butterdonut_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Check that rows and columns are valid
	if math.log2(rows) % 1 != 0 or math.log2(cols) % 1 != 0 or rows != cols:
		print("Error: ButterDonut topology is only applicable if both the number of rows and columns are a power of 2 and they are equal")
		sys.exit(1)
	# Compute intermediate values
	N = rows * cols
	stages = int(math.log2(rows))
	links = []
	# Add the horizontal links
	for row in range(rows):
		for col in range(cols):
			srow, scol = row, col
			drow, dcol = row, (min(col + 2, cols - 1) if col % 2 == 0 else max(col - 2, 0))
			(p1, p2) = (3, 0) if row < (rows // 2) else (2, 1)
			(p1, p2) = (p1, p2) if col % 2 == 0 else (p2, p1)
			p2 = p1 if dcol in [0, cols-1] else p2
			ep1 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p2}
			ep2 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p1}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1], "arc_factor" : 1.5})
	# Add the diagonal links
	for stage in range(stages):
		for scol in range(2**stage-1, cols, 2**(stage+1)):
			dcol = scol + 1
			for srow in range(rows):
				drow = ((srow // 2**(stage+1)) * 2**(stage+1)) + ((srow + 2**stage) % 2**(stage+1))
				p1 = 2 if srow < (rows//2) else 3
				p2 = 1 if drow < (rows//2) else 0
				ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p1}
				ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p2}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2], "arc_factor" : 100})
	# Return the links
	return links	

###############################################################################
# ClusCross Topology V1
###############################################################################

# The ClusCross-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_cluscross_v1_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Check that rows and columns are valid
	if rows % 2 != 0 or cols % 2 != 0 or rows < 4 or cols < 4:
		print("Error: ClusCross topology is only applicable if both the number of rows and columns are a multiple of 2. Also, both the number of rows and columns must be at least 4")
		sys.exit(1)
	# Compute intermediate values
	N = rows * cols
	stages = int(math.log2(rows))
	links = []
	# Add the special ClussCross links
	# Green
	(srow,scol,drow,dcol) = (rows//2-1,0,rows//2,cols-1)
	ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 1}
	ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 3}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2], "arc_factor" : 100})
	(srow,scol,drow,dcol) = (rows//2,0,rows//2-1,cols-1)
	ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 3}
	ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 1}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2], "arc_factor" : 100})
	# Red
	(srow,scol,drow,dcol) = (0,cols//2-1,rows-1,cols//2)
	ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 2}
	ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 0}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3], "arc_factor" : 100})
	(srow,scol,drow,dcol) = (0,cols//2,rows-1,cols//2-1)
	ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 0}
	ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 2}
	links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3], "arc_factor" : 100})
	# Yellow
	for col in [0,cols-1]:
		p = 0 if col == 0 else 2
		for row in range(rows//2):
			(srow,scol,drow,dcol) = (row,col,row+rows//2,col)
			ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p}
			ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[4], "arc_factor" : rows/3})
	# Purple
	for row in [0,rows-1]:
		p = 3 if row == 0 else 1
		for col in range(cols//2):
			(srow,scol,drow,dcol) = (row,col,row,col+cols//2)
			ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p}
			ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[5], "arc_factor" : rows/3})
	# Mesh-like links
	for row in range(rows):
		for col in range(cols):
			if (row not in [0,rows-1] or col != cols//2-1) and col < cols-1 :
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row * cols + col + 1, "inner_id" : 0}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1], "arc_factor" : 100})
			if (col not in [0,cols-1] or row != rows//2-1) and row < rows-1:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + col, "inner_id" : 3}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1], "arc_factor" : 100})
	# Return the links
	return links	


###############################################################################
# ClusCross Topology V2
###############################################################################

# The ClusCross-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_cluscross_v2_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	# Check that rows and columns are valid
	if rows % 2 != 0 or cols % 2 != 0 or rows < 4 or cols < 4:
		print("Error: ClusCross topology is only applicable if both the number of rows and columns are a multiple of 2. Also, both the number of rows and columns must be at least 4")
		sys.exit(1)
	# Compute intermediate values
	N = rows * cols
	stages = int(math.log2(rows))
	links = []
	# Add the special ClussCross links
	# Green
	for col in range(cols//2):
		(srow,scol,drow,dcol) = (rows//2-1,col,rows//2,col + cols//2)
		ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 1}
		ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 3}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2], "arc_factor" : 100})
		(srow,scol,drow,dcol) = (rows//2,col,rows//2-1,col + cols//2)
		ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 3}
		ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 1}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2], "arc_factor" : 100})
	# Red
	for col in range(1, cols-2, 2):
		(srow,scol,drow,dcol) = (0,col,rows-1,col+1)
		ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 3}
		ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 1}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3], "arc_factor" : 100})
		(srow,scol,drow,dcol) = (0,col+1,rows-1,col)
		ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : 3}
		ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : 1}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[3], "arc_factor" : 100})
	# Yellow
	for col in [0,cols-1]:
		p = 0 if col == 0 else 2
		for row in range(rows//2):
			(srow,scol,drow,dcol) = (row,col,row+rows//2,col)
			ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p}
			ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[4], "arc_factor" : rows/3})
	# Purple
	for row in [0,rows-1]:
		p = 3 if row == 0 else 1
		(srow,scol,drow,dcol) = (row,0,row,cols-1)
		ep1 = {"type" : "chiplet", "outer_id" : srow * cols + scol, "inner_id" : p}
		ep2 = {"type" : "chiplet", "outer_id" : drow * cols + dcol, "inner_id" : p}
		links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[5], "arc_factor" : rows/2})
	# Mesh-like links
	for row in range(rows):
		for col in range(cols):
			if col < cols-1:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 2}
				ep2 = {"type" : "chiplet", "outer_id" : row * cols + col + 1, "inner_id" : 0}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1], "arc_factor" : 100})
			if row != rows//2 -1 and row < rows-1:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : 1}
				ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + col, "inner_id" : 3}
				links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1], "arc_factor" : 100})
	# Return the links
	return links	

###############################################################################
# Kite Topology
###############################################################################

# The Kite-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_kite_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	patterns = params["patterns"]
	n = rows * cols
	links = []
	phy_count_map = {i : 0 for i in range(n)}
	# Iterate through the patterns
	for (pidx,super_pattern) in enumerate(patterns):
		for (hor, ver) in super_pattern:
			# Iterate through chiplets 
			for row in range(rows):
				for col in range(cols):
					src = row * cols + col	
					(drow, dcol) = (row + ver, col + hor)
					dst = drow * cols + dcol
					if drow >= 0 and drow < rows and dcol >= 0 and dcol < cols and phy_count_map[src] < 4 and phy_count_map[dst] < 4:
						ep1 = {"type" : "chiplet", "outer_id" : src, "inner_id" : phy_count_map[src]}
						ep2 = {"type" : "chiplet", "outer_id" : dst, "inner_id" : phy_count_map[dst]}
						links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[(pidx+1) % len(cfg.colors)]})
						phy_count_map[dst] += 1
						phy_count_map[src] += 1
	# Return the links
	return links	

def generate_kite_small_topology(params):
	patterns = [[(-1,1),(1,1)],[(1,0),(0,1)]]
	params["patterns"] = patterns
	return generate_kite_topology(params)

def generate_kite_medium_topology(params):
	patterns = [[(0,2),(2,0)],[(-1,1),(1,1)],[(1,0),(0,1)]]
	params["patterns"] = patterns
	return generate_kite_topology(params)

def generate_kite_large_topology(params):
	patterns = [[(-2,1),(-1,2),(1,2),(2,1)],[(0,2),(2,0)],[(-1,1),(1,1)],[(1,0),(0,1)]]
	params["patterns"] = patterns
	return generate_kite_topology(params)

###############################################################################
# SID-Mesh Topology
###############################################################################

# The SID-Mes is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
def generate_sid_mesh_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	n = rows * cols
	links = []
	# Add diagonal links
	for row in range(rows-1):
		for col in range(cols):
			src = row * cols + col
			for direction in [-1,1]:
				(drow, dcol) = (row + 1, col + direction)
				if drow >= 0 and drow < rows and dcol >= 0 and dcol < cols:
					dst = drow * cols + dcol
					p1 = 1 if direction == -1 else 2
					p2 = 3 if direction == -1 else 0
					ep1 = {"type" : "chiplet", "outer_id" : src, "inner_id" : p1}
					ep2 = {"type" : "chiplet", "outer_id" : dst, "inner_id" : p2}
					links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[1]})
	# Add horizontal border links
	for row in [0, rows-1]:
		for col in range(cols-1):
			(p1,p2) = (3,0) if row == 0 else (2,1)
			ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : row * cols + col + 1, "inner_id" : p2}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Add vertical border links
	for col in [0, cols-1]:
		for row in range(rows-1):
			(p1,p2) = (1,0) if col == 0 else (2,3)
			ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : p1}
			ep2 = {"type" : "chiplet", "outer_id" : (row + 1) * cols + col, "inner_id" : p2}
			links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[2]})
	# Return the links
	return links	


###############################################################################
# Spares Hamming Graph Topology
###############################################################################o

# The SHG-topology is only applicable to a grid-placement
# The generator function assumes that chiplet-ids start and the bottom-left corner
# and that they numbered in row-major order
# Parameters must contain:
# - rows: number of rows
# - cols: number of columns
# - shg_sr: horizontal express channels
# - shg_sc: vertical express channels
def generate_sparse_hamming_graph_topology(params):
	# Extract parameters
	rows = params["rows"]
	cols = params["cols"]
	sr = [1] + params["shg_sr"]
	sc = [1] + params["shg_sc"]
	links = []
	# Add horizontal express links
	h_phy_id_map = [0 for i in range(rows*cols)]
	for row in range(rows):
		for scol in range(cols):
			src = row * cols + scol
			for (i,hop) in enumerate(sr):
				dcol = scol + hop
				if dcol < cols:
					dst = row * cols + dcol
					ep1 = {"type" : "chiplet", "outer_id" : src, "inner_id" : h_phy_id_map[src]}
					ep2 = {"type" : "chiplet", "outer_id" : dst, "inner_id" : h_phy_id_map[dst]}
					links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[i % len(cfg.colors)]})
					h_phy_id_map[src] += 1
					h_phy_id_map[dst] += 1
	# Add vertical express links
	v_phy_id_map = [max(h_phy_id_map) for i in range(rows*cols)]
	for col in range(cols):
		for srow in range(rows):
			src = srow * cols + col
			for (i,hop) in enumerate(sc):
				drow = srow + hop
				if drow < rows:
					dst = drow * cols + col
					ep1 = {"type" : "chiplet", "outer_id" : src, "inner_id" : v_phy_id_map[src]}
					ep2 = {"type" : "chiplet", "outer_id" : dst, "inner_id" : v_phy_id_map[dst]}
					links.append({"ep1" : ep1, "ep2" : ep2, "color" : cfg.colors[len(sr) + (i % (len(cfg.colors) - len(sr)))]})
					v_phy_id_map[src] += 1
					v_phy_id_map[dst] += 1
	
	# Return the links
	return links	


topology_generation_functions = {
	"mesh" 					: generate_mesh_topology,
	"torus" 				: generate_torus_topology,
	"folded_torus" 			: generate_folded_torus_topology,
	"flattened_butterfly" 	: generate_flattened_butterfly_topology,
	"hexamesh" 				: generate_hexamesh_topology,
	"hexatorus" 			: generate_hexatorus_topology,
	"folded_hexatorus" 		: generate_folded_hexatorus_topology,
	"octamesh" 				: generate_octamesh_topology,
	"octatorus" 			: generate_octatorus_topology,
	"folded_octatorus" 		: generate_folded_octatorus_topology,
	"hypercube" 			: generate_hypercube_topology,
	"double_butterfly" 		: generate_double_butterfly_topology,
	"butterdonut"			: generate_butterdonut_topology,
	"cluscross_v1"			: generate_cluscross_v1_topology,
	"cluscross_v2"			: generate_cluscross_v2_topology,
	"kite_small"			: generate_kite_small_topology,
	"kite_medium"			: generate_kite_medium_topology,
	"kite_large"			: generate_kite_large_topology,
	"sid_mesh"				: generate_sid_mesh_topology,
	"sparse_hamming_graph"	: generate_sparse_hamming_graph_topology,
}

topology_to_placement = {
	"mesh" 					: "grid",
	"torus" 				: "grid",
	"folded_torus" 			: "grid",
	"flattened_butterfly" 	: "grid",
	"hexamesh" 				: "hexagonal",
	"hexatorus" 			: "hexagonal",
	"folded_hexatorus" 		: "hexagonal",
	"octamesh" 				: "grid",
	"octatorus" 			: "grid",
	"folded_octatorus" 		: "grid",
	"hypercube" 			: "grid",
	"double_butterfly" 		: "grid",
	"butterdonut"			: "grid",
	"cluscross_v1"			: "grid",
	"cluscross_v2"			: "grid",
	"kite_small"			: "grid",
	"kite_medium"			: "grid",
	"kite_large"			: "grid",
	"sid_mesh"				: "grid",
	"sparse_hamming_graph"	: "grid",
}

topology_to_phy_placement = {
	"mesh" 					: "4PHY_Edge",
	"torus" 				: "4PHY_Edge",
	"folded_torus" 			: "4PHY_Edge",
	"flattened_butterfly" 	: "xPHY_yPHY",
	"hexamesh" 				: "6PHY_HM",
	"hexatorus" 			: "6PHY_HM",
	"folded_hexatorus" 		: "6PHY_HM",
	"octamesh" 				: "8PHY_OM",		
	"octatorus" 			: "8PHY_OM",
	"folded_octatorus" 		: "8PHY_OM",
	"hypercube" 			: "xPHY_yPHY",
	"double_butterfly" 		: "4PHY_Corner",
	"butterdonut"			: "4PHY_Corner",
	"cluscross_v1"			: "4PHY_Edge",
	"cluscross_v2"			: "4PHY_Edge",
	"kite_small"			: "xPHY_yPHY",
	"kite_medium"			: "xPHY_yPHY",
	"kite_large"			: "xPHY_yPHY",
	"sid_mesh"				: "4PHY_Corner",
	"sparse_hamming_graph"	: "xPHY_yPHY",
}

