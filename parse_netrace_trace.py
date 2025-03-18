# Import python libraries
import argparse

# Import RapidChiplet files
import helpers as hlp

# Map take from table 2 in the netrace technical report
packet_type_to_size_map = {0:-1,1:1,2:9,3:9,4:9,5:1,6:9,13:1,14:1,15:1,16:9,25:1,27:1,28:1,29:1,30:9}

# trace_type_to_chiplet_type: dictionary mapping source- and destination types in the trace to chiplet types
# units_per_chiplet_type: dictionary mapping chiplet types to the number of units that are in a chiplet of a given type
# instances_per_chiplet_type: dictionary mapping chiplet types to the number of instances of a chiplet of a given type
def export_trace(input_file, output_file, trace_type_to_chiplet_type, units_per_chiplet_type, instances_per_chiplet_type, chiplet_id_list_per_chiplet_type):
	trace_in = hlp.read_json(input_file)
	num_nodes = trace_in['nodes']
	# Verify that the trace is applicable to the current chiplet configuration
	for chiplet_type in units_per_chiplet_type:
		if instances_per_chiplet_type[chiplet_type] * units_per_chiplet_type[chiplet_type] != num_nodes:
			print("ERROR: The number of nodes in the trace does not match the total number of units in chiplets of type \"" + chiplet_type + "\"")
			print("Number of nodes in the trace:", num_nodes)
			print("Number of units in chiplets of type \"" + chiplet_type + "\":", instances_per_chiplet_type[chiplet_type] * units_per_chiplet_type[chiplet_type])
	# Parse the trace
	packets_in = trace_in['packets']
	packets_out = []
	for packet_in in packets_in:
		source_chiplet_type = trace_type_to_chiplet_type[packet_in['src_type']]
		destination_chiplet_type = trace_type_to_chiplet_type[packet_in['dst_type']]
		source_chiplet_idx = packet_in['src'] // units_per_chiplet_type[source_chiplet_type]
		source_chiplet_id = chiplet_id_list_per_chiplet_type[source_chiplet_type][source_chiplet_idx]
		source_unit_id = packet_in['src'] % units_per_chiplet_type[source_chiplet_type]
		destination_chiplet_idx = packet_in['dst'] // units_per_chiplet_type[destination_chiplet_type]
		destination_chiplet_id = chiplet_id_list_per_chiplet_type[destination_chiplet_type][destination_chiplet_idx]
		destination_unit_id = packet_in['dst'] % units_per_chiplet_type[destination_chiplet_type]
		packet_size_in_flits = packet_type_to_size_map[packet_in['type']]
		packet_out = {}
		packet_out["id"] = packet_in["id"]
		packet_out["injection_cycle"] = packet_in["cycle"]
		packet_out["source_chiplet"] = source_chiplet_id
		packet_out["source_unit"] = source_unit_id
		packet_out["destination_chiplet"] = destination_chiplet_id
		packet_out["destination_unit"] = destination_unit_id
		packet_out["size_in_flits"] = packet_size_in_flits
		packet_out["reverse_dependencies"] = packet_in["reverse_dependencies"]
		packets_out.append(packet_out)
	hlp.write_json("inputs/traces/" + output_file, packets_out)


def gather_design_data_and_export_trace(inputs, input_file, output_file, trace_type_to_chiplet_type):
	# Load inputs if not already loaded
	required_inputs = ["chiplets","placement"]
	hlp.read_required_inputs(inputs, required_inputs)
	chiplets = inputs["chiplets"]
	placement = inputs["placement"]
	# Prepare the data for export_trace
	chiplet_types = set([chiplet["type"] for chiplet in chiplets.values()])
	units_per_chiplet_type = {ctype : [chiplet["unit_count"] for chiplet in chiplets.values() if chiplet["type"] == ctype] for ctype in chiplet_types}
	for ctype in units_per_chiplet_type:
		if len(set(units_per_chiplet_type[ctype])) != 1:
			print("ERROR: The number of units in chiplets of type \"" + ctype + "\" is not the same for all chiplets")
		units_per_chiplet_type[ctype] = units_per_chiplet_type[ctype][0]
	instances_per_chiplet_type = {ctype : sum([1 for c_desc in placement["chiplets"] if chiplets[c_desc["name"]]["type"] == ctype]) for ctype in chiplet_types}
	chiplet_id_list_per_chiplet_type = {ctype : [idx for (idx, c_desc) in enumerate(placement["chiplets"]) if chiplets[c_desc["name"]]["type"] == ctype] for ctype in chiplet_types}
	# Export the trace
	export_trace(input_file, output_file, trace_type_to_chiplet_type, units_per_chiplet_type, instances_per_chiplet_type, chiplet_id_list_per_chiplet_type)

def parse_netrace_trace(inputs, input_file, output_file):
	print("WARNING: The mapping from the memory hierarchy in the trace (L1, L2, Main Memory) to chiplet types in", end = "")
	print("the design is hard-coded in the script. Please verify that the mapping is correct.")
	# Mapping from the memory hierarchy in the trace to chiplet
	trace_type_to_chiplet_type = {
		"L1 Instruction Cache": "compute",
		"L1 Data Cache": "compute",
		"L2 Cache": "memory",
		"Memory Controller": "io",
	}
	# Export the trace
	gather_design_data_and_export_trace(inputs, input_file, output_file, trace_type_to_chiplet_type)


if __name__ == "__main__":
	# Read command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-df", "--design_file", required = True, help = "Path to the \"design\" input file")
	parser.add_argument("-if", "--input_file", required = True, help = "Path to the input trace file (usually in ./netrace/traces_out/)")
	parser.add_argument("-of", "--output_file", required = True, help = "Name of the output trace file (is stored in ./inputs/traces/)")
	args = parser.parse_args()
	# Read the design file
	inputs = {"design" : hlp.read_json(filename = args.design_file), "validate" : True, "verbose" : True}
	# Call the main function
	parse_netrace_trace(inputs, args.input_file, args.output_file)

