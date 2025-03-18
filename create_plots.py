# Python modules
import os
import sys
import argparse
import matplotlib.pyplot as plt

# RapidChiplet modules
import helpers as hlp

def create_latency_vs_load_plot(results):
	# Verify that the results file contains the necessary information
	if "booksim_simulation" not in results:
		print("The latency_vs_load plot requires the booksim_simulation results")
		sys.exit(1)
	# Prepare Plot
	(fig, ax) = plt.subplots(1,1, figsize=(3, 3))
	fig.subplots_adjust(left=0.2, right=0.99, top=0.99, bottom=0.15)
	loads = [float(x) for x in results["booksim_simulation"].keys() if hlp.is_float(x)]
	loads = sorted(loads)
	latencies = [results["booksim_simulation"][str(load)]["packet_latency"]["avg"] for load in loads]
	# Plot
	ax.plot(loads, latencies, marker='o')
	# Configure Axes
	ax.grid()
	ax.set_xlabel("Load")
	ax.set_ylabel("Latency (cycles)")
	# Save Plot
	plt.savefig("plots/latency_vs_load.pdf")

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-rf", "--results_file", type=str, help="Results file to plot", required=True)
	parser.add_argument("-pt", "--plot_type", type=str, help="Type of plot to create", required=True)
	args = parser.parse_args()
	results = hlp.read_json(args.results_file)
	if args.plot_type == "latency_vs_load":
		create_latency_vs_load_plot(results)
	else:	
		print("Invalid plot type \"%s\". Valid plot types are: latency_vs_load" % args.plot_type)

	
	








