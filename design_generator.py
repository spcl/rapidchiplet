# Import python libraries
import sys
import math

# Import RapidChiplet files
import helpers as hlp

# Note: This function only works if the width and height of all chiplet-types are identical
def generate_mesh(rows, cols, chiplets, c_chiplet_name, c_phy_map, m_chiplet_name = None, m_phy_map = None, i_chiplet_name = None, i_phy_map = None):
	# Load chiplets
	c_chiplet = chiplets["compute_chiplet_4phys"]
	m_chiplet = chiplets["compute_chiplet_4phys"] if m_chiplet_name else None
	i_chiplet = chiplets["compute_chiplet_4phys"] if i_chiplet_name else None
	# Extract chiplet dimensions
	(cw,ch) = (c_chiplet["dimensions"]["x"],c_chiplet["dimensions"]["y"])
	(mw,mh) = (m_chiplet["dimensions"]["x"],m_chiplet["dimensions"]["y"]) if m_chiplet_name else (0, 0)
	(iw,ih) = (i_chiplet["dimensions"]["x"],i_chiplet["dimensions"]["y"]) if i_chiplet_name else (0, 0)
	# Prepare the files to be generated
	placement = {"chiplets" : [], "interposer_routers" : []}
	topology = []
	# Add compute chiplets and links between them
	for row in range(rows):
		for col in range(cols):
			(x,y) = (mw + col * cw, ih + row * ch)
			placement["chiplets"].append({"position" : {"x" : x, "y" : y}, "rotation" : 0, "name" : c_chiplet_name})
			# Link to the west
			if col > 0:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : c_phy_map["W"]}
				ep2 = {"type" : "chiplet", "outer_id" : row * cols + (col-1), "inner_id" : c_phy_map["E"]}
				topology.append({"ep1" : ep1,"ep2" : ep2})
			# Link to the south
			if row > 0:
				ep1 = {"type" : "chiplet", "outer_id" : row * cols + col, "inner_id" : c_phy_map["S"]}
				ep2 = {"type" : "chiplet", "outer_id" : (row-1) * cols + col, "inner_id" : c_phy_map["N"]}
				topology.append({"ep1" : ep1,"ep2" : ep2})

	# Add memory chiplets if configured
	if m_chiplet_name:
		for row in range(rows):
			# Memory on left
			(x,y) = (0, ih + row * ch)
			rot = {"N" : 270, "E" : 0 ,"S" : 90, "W" : 180}[list(m_phy_map.keys())[0]]
			placement["chiplets"].append({"position" : {"x" : x, "y" : y}, "rotation" : rot, "name" : m_chiplet_name})
			# Links of left memories	
			ep1 = {"type" : "chiplet", "outer_id" : len(placement["chiplets"])-1, "inner_id" : 0}
			ep2 = {"type" : "chiplet", "outer_id" : row * cols + 0, "inner_id" : c_phy_map["W"]}
			topology.append({"ep1" : ep1,"ep2" : ep2})
			# Memory on right
			(x,y) = (mw + cols * cw, ih + row * ch)
			rot = {"N" : 90, "E" : 180 ,"S" : 270, "W" : 0}[list(m_phy_map.keys())[0]]
			placement["chiplets"].append({"position" : {"x" : x, "y" : y}, "rotation" : rot, "name" : m_chiplet_name})
			# Links of right memories	
			ep1 = {"type" : "chiplet", "outer_id" : len(placement["chiplets"])-1, "inner_id" : 0}
			ep2 = {"type" : "chiplet", "outer_id" : row * cols + (cols-1), "inner_id" : c_phy_map["E"]}
			topology.append({"ep1" : ep1,"ep2" : ep2})

	# Add IO chiplets if configured
	if i_chiplet_name:
		for col in range(cols):
			# IO on bottom
			(x,y) = (mw + col * cw, 0)
			rot = {"N" : 0, "E" : 270 ,"S" : 180, "W" : 90}[list(m_phy_map.keys())[0]]
			placement["chiplets"].append({"position" : {"x" : x, "y" : y}, "rotation" : rot, "name" : i_chiplet_name})
			# Links of bottom IOs	
			ep1 = {"type" : "chiplet", "outer_id" : len(placement["chiplets"])-1, "inner_id" : 0}
			ep2 = {"type" : "chiplet", "outer_id" : 0 * cols + col, "inner_id" : c_phy_map["S"]}
			topology.append({"ep1" : ep1,"ep2" : ep2})
			# IO on top
			(x,y) = (mw + col * cw, ih + rows * ch)
			rot = {"N" : 180, "E" : 90 ,"S" : 0, "W" : 270}[list(m_phy_map.keys())[0]]
			placement["chiplets"].append({"position" : {"x" : x, "y" : y}, "rotation" : rot, "name" : i_chiplet_name})
			# Links of top IOs	
			ep1 = {"type" : "chiplet", "outer_id" : len(placement["chiplets"])-1, "inner_id" : 0}
			ep2 = {"type" : "chiplet", "outer_id" : (rows-1) * cols + col, "inner_id" : c_phy_map["N"]}
			topology.append({"ep1" : ep1,"ep2" : ep2})
	
	# Return placement and topology	
	return (placement, topology)

# Note: This function only works if the width and height of all chiplet-types are identical
def generate_concentrated_mesh(rows, cols, concentration, chiplets, c_chiplet_name, c_phy_map, m_chiplet_name = None, m_phy_map = None, i_chiplet_name = None, i_phy_map = None):
	if math.sqrt(concentration) % 1 != 0:
		print("Error: The concentration must be a square number")
		sys.exit()
	con = int(math.sqrt(concentration))
	(crows, ccols)  = (rows * con, cols * con)
	# We use the function for the regular mesh to generate the placement
	(placement, _) = generate_mesh(crows, ccols, chiplets, c_chiplet_name, c_phy_map, m_chiplet_name, m_phy_map, i_chiplet_name, i_phy_map)
	topology = []
	# Load chiplets
	c_chiplet = chiplets["compute_chiplet_4phys"]
	m_chiplet = chiplets["compute_chiplet_4phys"] if m_chiplet_name else None
	i_chiplet = chiplets["compute_chiplet_4phys"] if i_chiplet_name else None
	# Extract chiplet dimensions
	(cw,ch) = (c_chiplet["dimensions"]["x"],c_chiplet["dimensions"]["y"])
	(mw,mh) = (m_chiplet["dimensions"]["x"],m_chiplet["dimensions"]["y"]) if m_chiplet_name else (0, 0)
	(iw,ih) = (i_chiplet["dimensions"]["x"],i_chiplet["dimensions"]["y"]) if i_chiplet_name else (0, 0)
	# Add interposer-routers for compute-cores
	for row in range(rows):
		for col in range(cols):
			(x,y) = (mw + (col + 0.5) * con * cw, ih + (row + 0.5) * con * ch)
			prts = concentration + 4
			placement["interposer_routers"].append({"position" : {"x" : x, "y" : y}, "ports" : prts})
	# Add interposer-routers for memory-chiplets
	if m_chiplet_name:
		for row in range(rows):
			# Left memories
			(x,y) = (mw, ih + (row + 0.5) * con * ch)
			prts = con + 1
			placement["interposer_routers"].append({"position" : {"x" : x, "y" : y}, "ports" : prts})
			# Right memories
			(x,y) = (mw + ccols * cw, ih + (row + 0.5) * con * ch)
			prts = con + 1
			placement["interposer_routers"].append({"position" : {"x" : x, "y" : y}, "ports" : prts})
	# Add interposer-routers for IO-chiplets
	if i_chiplet_name:
		for col in range(cols):
			# Bottom IOs 
			(x,y) = (mw + (col + 0.5) * con * cw, ih)
			prts = con + 1
			placement["interposer_routers"].append({"position" : {"x" : x, "y" : y}, "ports" : prts})
			# Top IOs 
			(x,y) = (mw + (col + 0.5) * con * cw, ih + crows * ch)
			prts = con + 1
			placement["interposer_routers"].append({"position" : {"x" : x, "y" : y}, "ports" : prts})
	# Construct topology
	topology = []
	port_map = [0 for x in range(len(placement["interposer_routers"]))]
	# Add links connecting compute-chiplets to irouters
	for crow in range(crows):
		for ccol in range(ccols):
			cid = crow * ccols + ccol
			(row, col) = (crow // con, ccol // con)
			rid = row * cols + col
			ep1 = {"type" : "chiplet", "outer_id" : cid, "inner_id" : 0}
			ep2 = {"type" : "irouter", "outer_id" : rid, "inner_id" : port_map[rid]}
			port_map[rid] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
	# Add links connecting memory-chiplets to irouters
	if m_chiplet_name:
		for crow in range(crows):
			# Memory on left 
			cid = crows * ccols + 2 * crow
			rid = rows * cols + 2 * (crow // con)
			ep1 = {"type" : "chiplet", "outer_id" : cid, "inner_id" : 0}
			ep2 = {"type" : "irouter", "outer_id" : rid, "inner_id" : port_map[rid]}
			port_map[rid] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
			# Memory on right
			cid = crows * ccols + 2 * crow + 1
			rid = rows * cols + 2 * (crow // con) + 1
			ep1 = {"type" : "chiplet", "outer_id" : cid, "inner_id" : 0}
			ep2 = {"type" : "irouter", "outer_id" : rid, "inner_id" : port_map[rid]}
			port_map[rid] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
	# Add links connecting IO-chiplets to irouters
	if i_chiplet_name:
		for ccol in range(ccols):
			# Memory on left 
			cid = crows * ccols + ((2 * crows) if m_chiplet_name else 0) + 2 * ccol
			rid = rows * cols + ((2 * rows) if m_chiplet_name else 0) + 2 * (ccol // con)
			ep1 = {"type" : "chiplet", "outer_id" : cid, "inner_id" : 0}
			ep2 = {"type" : "irouter", "outer_id" : rid, "inner_id" : port_map[rid]}
			port_map[rid] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
			# Memory on right
			cid = crows * ccols + ((2 * crows) if m_chiplet_name else 0) + 2 * ccol + 1
			rid = rows * cols + ((2 * rows) if m_chiplet_name else 0) + 2 * (ccol // con) + 1
			ep1 = {"type" : "chiplet", "outer_id" : cid, "inner_id" : 0}
			ep2 = {"type" : "irouter", "outer_id" : rid, "inner_id" : port_map[rid]}
			port_map[rid] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
	# Add mesh between irouters
	for row in range(rows):
		for col in range(cols):
			# Horizontal
			if col < cols-1:
				rid1 = row * cols + col
				rid2 = row * cols + (col + 1)
				ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
				ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
				port_map[rid1] += 1
				port_map[rid2] += 1
				topology.append({"ep1" : ep1, "ep2" : ep2})
			# Vertical 
			if row < rows - 1:
				rid1 = row * cols + col
				rid2 = (row + 1) * cols + col
				ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
				ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
				port_map[rid1] += 1
				port_map[rid2] += 1
				topology.append({"ep1" : ep1, "ep2" : ep2})
	# Connect memory-irouters to rest
	if m_chiplet_name:
		for row in range(rows):
			# Memory on the left
			rid1 = row * cols
			rid2 = rows * cols + 2 * row
			ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
			ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
			port_map[rid1] += 1
			port_map[rid2] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
			# Memory on the left
			rid1 = row * cols + (cols - 1)
			rid2 = rows * cols + 2 * row + 1
			ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
			ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
			port_map[rid1] += 1
			port_map[rid2] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
	# Connect memory-irouters to rest
	if i_chiplet_name:
		for col in range(rows):
			# IO on the bottom
			rid1 = col
			rid2 = rows * cols + ((2 * rows) if m_chiplet_name else 0) + 2 * col
			ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
			ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
			port_map[rid1] += 1
			port_map[rid2] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
			# IO on the bottom
			rid1 = (rows - 1) * cols + col
			rid2 = rows * cols + ((2 * rows) if m_chiplet_name else 0) + 2 * col + 1
			ep1 = {"type" : "irouter", "outer_id" : rid1, "inner_id" : port_map[rid1]}
			ep2 = {"type" : "irouter", "outer_id" : rid2, "inner_id" : port_map[rid2]}
			port_map[rid1] += 1
			port_map[rid2] += 1
			topology.append({"ep1" : ep1, "ep2" : ep2})
	# Return placement and topology	
	return (placement, topology)


