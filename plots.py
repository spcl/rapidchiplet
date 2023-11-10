# Import python libraries
import os
import matplotlib.pyplot as plt

# Import RapidChiplet Files
import helpers as hlp

# Colors and markers for plotting
colors = ["#990099","#999900","#000099","#006600","#00aa66","#22dd99","#990000","#0066cc","#66ccff","#000000"]
markers = ["o","d","s","x","+","^","*","D","p","h"]

# Create the runtime plot
def create_runtime_plot(max_size, reps):
	# Initialize plot
	(fig, ax) = plt.subplots(1, 2, figsize = (6, 3))
	plt.subplots_adjust(left=0.12, right = 0.995, top = 0.92, bottom = 0.25, wspace = 0.35)
	sizes = list(range(2,max_size + 1))
	# Iterate through topologies
	for (i, topo) in enumerate(["mesh","cmesh"]):
		data = {}
		# Iterate through scales
		for x in sizes:
			# Iterate through repetitions
			for rep in range(reps):
				# Read measurements
				path = "results/%s_%dx%d_%d.json" % (topo,x,x,rep)	
				if os.path.exists(path):
					results = hlp.read_file(path)
					for key in results["runtime"]:
						if key not in data:
							data[key] = {}
						if x not in data[key]:
							data[key][x] = []
						data[key][x].append(results["runtime"][key])
		# Iterate through the single timing metrics
		for (j, key) in enumerate(data):
			xvals = list(data[key].keys())
			yvals = [sum(x) / len(x) for x in data[key].values()]
			ylow = [min(x) for x in data[key].values()]
			yhigh = [max(x) for x in data[key].values()]
			# Plot a given timing metric
			ax[i].plot(xvals, yvals, label = key, markersize = 3, marker = markers[j], color = colors[j], linewidth = 1, markerfacecolor = "none")
			ax[i].fill_between(xvals, ylow, yhigh, color = colors[j], alpha = 0.5)
		# Configure the sub-plot
		sizes_ = sizes if topo == "mesh" else [x for x in sizes if x%2==0]
		ax[i].set_title("2D Mesh" if topo == "mesh" else "Concentrated 2D Mesh")
		ax[i].grid(which = "major", linewidth = 1.0, axis = "y", color = "#666666")
		ax[i].grid(which = "minor", linewidth = 0.25, axis = "y", color = "#666666")
		ax[i].set_xticks(sizes_)
		ax[i].set_xticklabels(["%dx%d" % (x,x) for x in sizes_], rotation = 90)
		ax[i].set_xlabel("Scale")
		ax[i].set_ylabel("Runtime [s]")
		ax[i].set_yscale("log")
		ax[i].set_yticks([10**x for x in range(-6,1)])
		ax[i].set_xlim(1.5,max_size + 0.5)
		ax[i].set_ylim(1e-6,1e0)
	# Save the plot
	plt.savefig("plots/runtime.pdf")

# Create the accuracy plot
def create_accuracy_plot(max_size):
	# One plot for latency, one for throughput
	for metric in ["latency","throughput"]:
		(fig, ax) = plt.subplots(1, 2, figsize = (6, 2.5))
		plt.subplots_adjust(left=0.093, right = 0.99, top = 0.9, bottom = 0.3, wspace = 0.3)
		sizes = list(range(2,max_size + 1))
		# One subplot per topology
		for (i, topo) in enumerate(["mesh","cmesh"]):
			# One data series per traffic class
			for (j, traffic) in enumerate(["C2C","C2M","C2I","M2I"]):
				# Read data
				metric_rc = {}
				metric_bs = {}
				for x in sizes:
					path_rc = "results/%s_%dx%d_%d.json" % (topo,x,x,0)	
					path_bs = "results/sim_%s_%dx%d_%s.json" % (topo,x,x,traffic)	
					# RapidChiplet
					if os.path.exists(path_rc):
						results_rc = hlp.read_file(path_rc)
						if metric == "latency":
							metric_rc[x] = results_rc["ici_latency"][traffic]["avg"]
						else:
							metric_rc[x] = 100 * results_rc["ici_throughput"][traffic]["fraction_of_theoretical_peak"]
					# BookSim
					if os.path.exists(path_bs):
						results_bs = hlp.read_file(path_bs)
						if metric == "latency":
							metric_bs[x] = results_bs["0.001"]["packet_latency"]["avg"]
						else:
							metric_bs[x] = 100 * max([float(key) for key in results_bs if float(key) <= 3 * results_bs["0.001"]["packet_latency"]["avg"]])
				# Plot data
				colors1 = ["#000066","#006600","#660000","#660066"]
				colors2 = ["#6666FF","#66FF66","#FF6666","#FF66FF"]
				# RapidChiplet
				xvals = list(metric_rc.keys())
				yvals = list(metric_rc.values())
				ax[i].plot(xvals, yvals, label = traffic + " (RC)", markersize = 3, marker = markers[j+4], color = colors1[j], linewidth = 1, markerfacecolor = "none", linestyle = "--")
				# BookSim 
				xvals = list(metric_bs.keys())
				yvals = list(metric_bs.values())
				ax[i].plot(xvals, yvals, label = traffic + " (BS)", markersize = 3, marker = markers[j+4], color = colors2[j], linewidth = 1, markerfacecolor = "none", linestyle = ":")
				# Compute and print average relative error
				rel_errors = []
				for x in sizes:
					if x in metric_rc and x in metric_bs:
						rel_errors.append(abs(metric_rc[x] - metric_bs[x]) / metric_bs[x])
				if len(rel_errors) > 0:
					avg_rel_error = sum(rel_errors) / len(rel_errors) * 100
					print("%s %s %s AVG relative error: %.2f%%" % (metric, topo, traffic, avg_rel_error))

			# Configure the sub-plot
			real_sizes = sizes if topo == "mesh" else [x for x in sizes if x%2==0]
			ax[i].set_title("2D Mesh" if topo == "mesh" else "Concentrated 2D Mesh")
			ax[i].grid(which = "major", linewidth = 1.0, axis = "y", color = "#666666")
			ax[i].grid(which = "minor", linewidth = 0.25, axis = "y", color = "#666666")
			ax[i].set_xticks(real_sizes)
			ax[i].set_xticklabels(["%dx%d" % (x,x) for x in real_sizes], rotation = 90)
			ax[i].set_xlabel("Scale")
			ax[i].set_ylabel("Latency [cycles]" if metric == "latency" else "Throughput [%]")
			if metric == "throughput":
				ax[i].set_ylim(bottom = 0)
			if metric == "latency" and i == 0:	
				ax[i].set_ylim(0,600)
			if metric == "latency" and i == 1:	
				ax[i].set_ylim(0,150)
			ax[i].set_xlim(1.5,max_size + 0.5)
		# Store the plot
		plt.savefig("plots/accuracy_%s.pdf" % metric)

# Create the accuracy plot
def create_speedup_plot(max_size):
	# One plot for latency, one for throughput
	for metric in ["latency","throughput"]:
		(fig, ax) = plt.subplots(1, 2, figsize = (6, 2.5))
		plt.subplots_adjust(left=0.11, right = 0.99, top = 0.89, bottom = 0.3, wspace = 0.35)
		sizes = list(range(2,max_size + 1))
		# One subplot per topology
		for (i, topo) in enumerate(["mesh","cmesh"]):
			# One data series for RapidChiplet
			time_rc = {}
			# Three data series for BookSim (10%, 1%, 0.1% precision)
			time_bs_1 = {}
			time_bs_2 = {}
			time_bs_3 = {}
			# Read data
			for x in sizes:
				path_rc = "results/%s_%dx%d_%d.json" % (topo,x,x,0)	
				# Read RapidChiplet data
				if os.path.exists(path_rc):
					results_rc = hlp.read_file(path_rc)
					time_rc[x] = results_rc["runtime"]["total_runtime"]
				# Read BookSim data
				for (j, traffic) in enumerate(["C2C","C2M","C2I","M2I"]):
					path_bs = "results/sim_%s_%dx%d_%s.json" % (topo,x,x,traffic)	
					if os.path.exists(path_bs):
						if x not in time_bs_1:
							time_bs_1[x] = 0
						if x not in time_bs_2:
							time_bs_2[x] = 0
						if x not in time_bs_3:
							time_bs_3[x] = 0
						results_bs = hlp.read_file(path_bs)
						if metric == "latency":
							time_bs_1[x] += results_bs["0.001"]["total_run_time"]
						else:
							time_bs_1[x] += sum([results_bs[load]["total_run_time"] for load in results_bs if round(float(load),1) == float(load)])
							time_bs_2[x] += sum([results_bs[load]["total_run_time"] for load in results_bs if round(float(load),2) == float(load)])
							time_bs_3[x] += sum([results_bs[load]["total_run_time"] for load in results_bs if round(float(load),3) == float(load)])
			# Plot RapidChiplet data
			xvals = list(time_rc.keys())
			yvals = list(time_rc.values())
			ax[i].plot(xvals, yvals, label = traffic + " (RC)", markersize = 3, marker = "o", color = "#000000", linewidth = 1, markerfacecolor = "none", linestyle = "--")
			# Plot BookSim data
			if len(time_bs_1) > 0:
				xvals = list(time_bs_1.keys())
				yvals = list(time_bs_1.values())
				ax[i].plot(xvals, yvals, label = traffic + " (BS)", markersize = 3, marker = "s", color = "#000099", linewidth = 1, markerfacecolor = "none", linestyle = ":")
			if len(time_bs_2) > 0:
				xvals = list(time_bs_2.keys())
				yvals = list(time_bs_2.values())
				ax[i].plot(xvals, yvals, label = traffic + " (BS)", markersize = 3, marker = "D", color = "#009900", linewidth = 1, markerfacecolor = "none", linestyle = ":")
			if len(time_bs_3) > 0:
				xvals = list(time_bs_3.keys())
				yvals = list(time_bs_3.values())
				ax[i].plot(xvals, yvals, label = traffic + " (BS)", markersize = 3, marker = "P", color = "#990000", linewidth = 1, markerfacecolor = "none", linestyle = ":")
			# Compute and print speedups 
			speedups_1 = []
			speedups_2 = []
			speedups_3 = []
			for x in sizes:
				if x in time_rc and x in time_bs_1:
					speedups_1.append(time_bs_1[x] / time_rc[x])
				if x in time_rc and x in time_bs_2:
					speedups_2.append(time_bs_2[x] / time_rc[x])
				if x in time_rc and x in time_bs_3:
					speedups_3.append(time_bs_3[x] / time_rc[x])
			if len(speedups_1) > 0:
				avg_speedup = sum(speedups_1) / len(speedups_1)
				print("%s %s AVG speedup 10%%: %.2fx" % (metric, topo, avg_speedup))
			if len(speedups_2) > 0:
				avg_speedup = sum(speedups_2) / len(speedups_2)
				print("%s %s AVG speedup 1%%: %.2fx" % (metric, topo, avg_speedup))
			if len(speedups_3) > 0:
				avg_speedup = sum(speedups_3) / len(speedups_3)
				print("%s %s AVG speedup 0.1%%: %.2fx" % (metric, topo, avg_speedup))
			# Configure sub-plot
			real_sizes = sizes if topo == "mesh" else [x for x in sizes if x%2==0]
			ax[i].set_title("2D Mesh" if topo == "mesh" else "Concentrated 2D Mesh")
			ax[i].grid(which = "major", linewidth = 1.0, axis = "y", color = "#666666")
			ax[i].grid(which = "minor", linewidth = 0.25, axis = "y", color = "#666666")
			ax[i].set_xticks(real_sizes)
			ax[i].set_xticklabels(["%dx%d" % (x,x) for x in real_sizes], rotation = 90)
			ax[i].set_xlabel("Scale")
			ax[i].set_ylabel("Runtime [s]")
			ax[i].set_yscale("log")
			if metric == "latency":
				ax[i].set_ylim(1e-3,1e1)
			else:
				ax[i].set_yticks([10**x for x in range(-3,4,1)])
				ax[i].set_ylim(1e-3*0.7,1e3*1.3)
			ax[i].set_xlim(1.5,max_size + 0.5)
		# Store plot
		plt.savefig("plots/speedup_%s.pdf" % metric)

def reproduce_plots_from_paper(reps, max_size):
	create_runtime_plot(max_size, reps)
	create_accuracy_plot(max_size)
	create_speedup_plot(max_size)
