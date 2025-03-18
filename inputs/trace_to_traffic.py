# Python modules
import argparse
import sys
import os


# RapidChiplet modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
import helpers as hlp 


def convert_trace_to_traffic(trace):
	# Convert trace to traffic
	traffic = {}
	for packet in trace:
		src_node = (packet["source_chiplet"], packet["source_unit"])
		dst_node = (packet["destination_chiplet"], packet["destination_unit"])
		n_flits = packet["size_in_flits"]
		if (src_node, dst_node) not in traffic:
			traffic[(src_node, dst_node)] = 0
		traffic[(src_node, dst_node)] += n_flits
	# Divide the traffic entries by the total number of cycle that the trace covers
	min_cycle = min([packet["injection_cycle"] for packet in trace])
	max_cycle = max([packet["injection_cycle"] for packet in trace])
	total_cycles = max_cycle - min_cycle
	for key in traffic:
		traffic[key] /= total_cycles
	# Return the traffic
	return traffic

def trace_to_traffic(trace_file, output_file):
	trace = hlp.read_json(trace_file)
	traffic = convert_trace_to_traffic(trace)
	# Store results
	hlp.write_json("./traffic_by_unit/%s.json" % output_file, traffic)
	traffic_by_chiplet = hlp.convert_by_unit_traffic_to_by_chiplet_traffic(traffic)
	hlp.write_json("./traffic_by_chiplet/%s.json" % output_file, traffic_by_chiplet)

if __name__ == "__main__":
	# Convert trace to traffic
	parser = argparse.ArgumentParser()
	parser.add_argument("-if", "--input_file", required = True, help = "Path to the \"trace\" input file")
	parser.add_argument("-of", "--output_file", required = True, help = "Name of the \"traffic\" output file (stored in ./traffic_by_unit/ and ./traffic_by_chiplet/")
	args = parser.parse_args()
	trace_to_traffic(args.input_file, args.output_file)

