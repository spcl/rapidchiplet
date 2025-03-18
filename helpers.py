# Python libraries
import json
import copy
import math

# RapidChiplet libraries
import rapidchiplet as rc
import validation as val

# Check if a string can be converted to an float
def is_float(value):
	try:
		float(value)
		return True
	except ValueError:
		return False

# Used for JSON encoding / decoding of python objects
def encode_key(key):
    if isinstance(key, tuple):
        return '__tuple__:' + json.dumps([encode_key(k) for k in key])
    return key

# Used for JSON encoding / decoding of python objects
def decode_key(key):
    if isinstance(key, str) and key.startswith('__tuple__:'):
        return tuple(decode_key(k) for k in json.loads(key[len('__tuple__:'):]))
    return key

# Used for JSON encoding / decoding of python objects
def encode_data(data):
    if isinstance(data, dict):
        return {encode_key(k): encode_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [encode_data(item) for item in data]
    elif isinstance(data, tuple):
        return {'__tuple__': True, 'items': [encode_data(item) for item in data]}
    else:
        return data

# Used for JSON encoding / decoding of python objects
def decode_data(data):
    if isinstance(data, dict):
        if '__tuple__' in data:
            return tuple(decode_data(item) for item in data['items'])
        else:
            return {decode_key(k): decode_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decode_data(item) for item in data]
    else:
        return data

# Write a JSON file
def write_json(filename, content):
    file = open(filename, "w")
    file.write(json.dumps(encode_data(content), indent=4))
    file.close()

# Read a JSON file
def read_json(filename):
    file = open(filename, "r")
    file_content = decode_data(json.loads(file.read()))
    file.close()
    return file_content

# Read inputs if they are not already present
def read_required_inputs(inputs, required_inputs):
	design = inputs["design"]
	for input_name in required_inputs:
		if input_name not in inputs:
			inputs[input_name] = read_json(design[input_name])
			val.validation_functions[input_name](inputs)

# Compute intermediates if they are not already present
def compute_required_intermediates(inputs, intermediates, required_intermediates):
	for intermediate_name in required_intermediates:
		if intermediate_name not in intermediates:
			intermediates[intermediate_name] = rc.metric_computation_functions[intermediate_name](inputs, intermediates)

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
    if rot % 2 == 1:
        chiplet["dimensions"] = {"x" : chiplet["dimensions"]["y"],"y" : chiplet["dimensions"]["x"]}
    (cxn, cyn) = (chiplet["dimensions"]["x"] / 2, chiplet["dimensions"]["y"] / 2)
    for (pid, phy) in enumerate(chiplet["phys"]):
        (x, y) = (phy["x"] - cx, phy["y"] - cy)
        (xr,yr) = (x * math.cos(alpha) - y * math.sin(alpha), x * math.sin(alpha) + y * math.cos(alpha))
        chiplet["phys"][pid] = {"x" : cxn + xr, "y" : cyn + yr}
    # Return a rotated copy of the chiplet
    return chiplet

# Construct a graph representation of the ICI network
def construct_ici_graph(chiplets, placement, topology):
	# List of nodes. Nodes are labeled with (type, id), e.g., (chiplet, 0) or (irouter, 7)
	nodes = []
	# Map that specifies whether a node can relay traffic to another node
	relay_map = {}
	# Adjacency list
	adj_list = {}
	# Inspect the placement to specify nodes and relay_map, also initialize adj_list
	for (cid, chiplet_desc) in enumerate(placement["chiplets"]):
		node = ("chiplet", cid)
		nodes.append(node)
		relay_map[node] = chiplets[chiplet_desc["name"]]["relay"]
		adj_list[node] = []
	for (rid, irouter_desc) in enumerate(placement["interposer_routers"]):
		node = ("irouter", rid)
		nodes.append(node)
		relay_map[node] = True
		adj_list[node] = []
	# Inspect the topology to specify adj_list
	for link in topology:
		node_1 = (link["ep1"]["type"], link["ep1"]["outer_id"])
		node_2 = (link["ep2"]["type"], link["ep2"]["outer_id"])
		adj_list[node_1].append(node_2)
		adj_list[node_2].append(node_1)
	# Sort the adjacency lists
	for node in adj_list:
		adj_list[node].sort(key = lambda x: (0 if x[0] == "chiplet" else 1, x[1]))
	# Return the constructed graph
	return {"nodes": nodes, "relay_map": relay_map, "adj_list": adj_list}

def convert_by_unit_traffic_to_by_chiplet_traffic(traffic_by_unit):
	traffic_by_chiplet = {}
	for ((src_cid, src_uid),(dst_cid, dst_uid)) in traffic_by_unit.keys():
		new_key = (src_cid, dst_cid)
		if new_key not in traffic_by_chiplet:
			traffic_by_chiplet[new_key] = 0
		traffic_by_chiplet[new_key] += traffic_by_unit[((src_cid, src_uid),(dst_cid, dst_uid))]
	return traffic_by_chiplet
