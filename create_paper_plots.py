# Python modules
import os
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# RapidChiplet modules
import helpers as hlp
import global_config as cfg
import run_experiment as re 

def read_results(prefix, suffix, n_units):
	data = {}
	results_lat = hlp.read_json("results/%slatency%s.json" % (prefix, suffix))
	results_tp = hlp.read_json("results/%sthroughput%s.json" % (prefix, suffix))
	results_bs = hlp.read_json("results/%sbooksim%s.json" % (prefix, suffix))
	results_link = hlp.read_json("results/%slinks%s.json" % (prefix, suffix))
	data["latency"] = results_lat["latency"]["avg"]
	data["throughput"] = results_tp["throughput"]["aggregate_throughput"]
	data["bs_latency"] = results_bs["booksim_simulation"]["0.001"]["packet_latency"]["avg"]
	data["runtime_lat"] = results_lat["latency"]["time_taken"]
	data["runtime_tp"] = results_tp["throughput"]["time_taken"]
	data["bs_runtime_lat"] = results_bs["booksim_simulation"]["0.001"]["total_run_time"]
	data["bs_runtime_tp"] = sum([results_bs["booksim_simulation"][x]["total_run_time"] for x in results_bs["booksim_simulation"].keys() if hlp.is_float(x)])
	# We need to transform the injection rate reported by BookSim into the aggregate throughput reported by RapidChiplet
	max_inj_rate = max([float(x) for x in results_bs["booksim_simulation"].keys() if hlp.is_float(x)])
	if results_link["link_summary"]["bandwidths"]["min"] == results_link["link_summary"]["bandwidths"]["max"]:
		link_bw = results_link["link_summary"]["bandwidths"]["min"]
	else:
		print("ERROR: Link bandwidths are not uniform")
		sys.exit(1)
	data["bs_throughput"] = max_inj_rate * link_bw * n_units
	return data	
			
def create_evaluation_plot():
	# Plot settings
	colors = cfg.colors
	markers = ["o","s","D","p"]
	# Load the BookSim part of the evaluation.
	# Parameters should be identical for the latency and throughput parts.
	experiment = hlp.read_json("experiments/evaluation_booksim.json")
	experiment_name = "evaluation"
	del experiment["exp_name"]
	del experiment["metrics"]
	(base_params, ranged_params) = re.split_parameters(experiment)
	units_per_chiplet = base_params["units_per_chiplet"]
	scales = ranged_params["grid_scale"]
	topologies = ranged_params["topology"]
	traffics = ranged_params["traffic_pattern"]
	# Create a list of files that contain the results needed for the accuracy plot
	data = []
	for topology in topologies:
		for scale in scales:
			for traffic in traffics:
				prefix = experiment_name + "_"
				suffix = "-%s-%s-%s" % (topology, scale, traffic)
				n_chiplets = int(scale.split("x")[0]) * int(scale.split("x")[1])
				n_units = n_chiplets * units_per_chiplet
				entry = read_results(prefix, suffix, n_units)
				entry["topology"] = topology
				entry["scale"] = scale
				entry["traffic"] = traffic
				data.append(entry)
	# Create the plot
	(fig, ax) = plt.subplots(4, 4, figsize=(10, 12))
	fig.subplots_adjust(left=0.1, right=0.99, top=0.975, bottom=0.075, hspace=0.1, wspace=0.1)
	limits = [[float("inf"),-float("inf")] for i in range(4)]
	values = [("Latency Error", []), ("Latency Speedup", []), ("Throughput Error", []), ("Throughput Speedup", [])]
	# Iterate through traffic patterns (subplots):
	for (i, traffic) in enumerate(traffics):
		ax[0][i].set_title(" ".join([x.capitalize() for x in traffic.split("_")]))
		# Iterate through topologies (lines):
		for (j, topology) in enumerate(topologies):
			filtered_data = [x for x in data if x["traffic"] == traffic and x["topology"] == topology]
			filtered_data = sorted(filtered_data, key=lambda x: int(x["scale"].split("x")[0]))
			xvals = [x["scale"] for x in filtered_data]
			lat_err = [(x["latency"] / x["bs_latency"] -1.0) * 100 for x in filtered_data]
			tp_err = [(x["throughput"] / x["bs_throughput"] -1.0) * 100 for x in filtered_data]
			lat_spu = [(x["bs_runtime_lat"] / x["runtime_lat"] if x["runtime_lat"] > 0 else float("nan")) for x in filtered_data]
			tp_spu = [(x["bs_runtime_tp"] / x["runtime_tp"] if x["runtime_tp"] > 0 else float("nan")) for x in filtered_data]
			metrics = [lat_err, lat_spu, tp_err, tp_spu]
			for (k, metric) in enumerate(metrics):
				ax[k][i].plot(xvals, metric, label=topology, marker=markers[j], color=colors[j])
				limits[k][0] = min(limits[k][0], min(metric))
				limits[k][1] = max(limits[k][1], max(metric))
				values[k][1].append(sum([abs(x) for x in metric]) / len(metric))
				# Add a horizontal line at 0 for the error plots
				if k % 2 == 0:
					ax[k][i].axhline(0, color="black", linestyle="--")
	# Add average per subplot
	for i in range(4):
		for j in range(len(traffics)):
			vals = values[i][1][4*j:4*(j+1)]
			avg = sum(vals) / len(vals)
			if "Error" in values[i][0]:
				ax[i][j].text(0.5, 0.95, "Average: %.2f%%" % avg, ha="center", va="top", transform=ax[i][j].transAxes, fontweight="bold")
			else:
				ax[i][j].text(0.5, 0.95, "Average: %.0fx" % avg, ha="center", va="top", transform=ax[i][j].transAxes, fontweight="bold")

	# Y-labels
	ax[0][0].set_ylabel("Latency Error [%]")
	ax[1][0].set_ylabel("Latency Speedup")
	ax[2][0].set_ylabel("Throughput Error [%]")
	ax[3][0].set_ylabel("Throughput Speedup")
	# General y-axis settings
	for (i, limit) in enumerate(limits):
		for (j, traffic) in enumerate(traffics):
			# Y-Limit
			ax[i][j].set_ylim(limit[0], limit[1])
			# Grid
			ax[i][j].grid(which="both", color = "#666666")
			# Y-Axis in percent for error plots
			if i == 3:
				ax[i][j].set_yscale("log")
			ax[i][j].set_yticks(ax[i][j].get_yticks()[1:-1])
			if i % 2 == 0:
				ax[i][j].yaxis.set_major_formatter(mtick.PercentFormatter())
			# Only show Y-Tick labels on the left-most subplots
			if j > 0:
				ax[i][j].set_yticklabels([])
	# General x-axis settings
	for i in range(4):
		for j in range(len(traffics)):
			ax[i][j].set_xticks(range(len(scales)))
			if i == 3:	
				ax[i][j].set_xlabel("Number of Chiplets")
				ax[i][j].set_xticklabels(scales, rotation=90)
			else:
				ax[i][j].set_xticklabels([])
	# Save the plot
	plt.savefig("plots/evaluation.pdf")
	# Print the average values
	for (name, values) in values:
		print("Average %s: %.3f %s" % (name, sum(values) / len(values), "%" if "Error" in name else ""))

def create_extended_evaluation_plot():
	colors = cfg.colors
	markers = ["o","s","D","p"]
	experiment = hlp.read_json("experiments/evaluation_booksim.json")
	experiment_name = "evaluation"
	del experiment["exp_name"]
	del experiment["metrics"]
	(base_params, ranged_params) = re.split_parameters(experiment)
	units_per_chiplet = base_params["units_per_chiplet"]
	scales = ranged_params["grid_scale"]
	topologies = ranged_params["topology"]
	traffics = ranged_params["traffic_pattern"]
	# Create a list of files that contain the results needed for the accuracy plot
	data = []
	for topology in topologies:
		for scale in scales:
			for traffic in traffics:
				prefix = experiment_name + "_"
				suffix = "-%s-%s-%s" % (topology, scale, traffic)
				n_chiplets = int(scale.split("x")[0]) * int(scale.split("x")[1])
				n_units = n_chiplets * units_per_chiplet
				entry = read_results(prefix, suffix, n_units)
				entry["topology"] = topology
				entry["scale"] = scale
				entry["traffic"] = traffic
				data.append(entry)
	# Create the plot
	(fig, ax) = plt.subplots(8, 4, figsize=(10, 24))
	fig.subplots_adjust(left=0.1, right=0.99, top=0.975, bottom=0.05, hspace=0.1, wspace=0.1)
	limits = [[float("inf"),-float("inf")] for i in range(8)]
	values = [("Latency", []), ("BookSim Latency", []), ("Throughput", []), ("BookSim Throughput", []), ("Latency Runtime", []), ("BookSim Latency Runtime", []), ("Throughput Runtime", []), ("BookSim Throughput Runtime", [])]
	# Iterate through traffic patterns (subplots):
	for (i, traffic) in enumerate(traffics):
		ax[0][i].set_title(" ".join([x.capitalize() for x in traffic.split("_")]))
		# Iterate through topologies (lines):
		for (j, topology) in enumerate(topologies):
			filtered_data = [x for x in data if x["traffic"] == traffic and x["topology"] == topology]
			filtered_data = sorted(filtered_data, key=lambda x: int(x["scale"].split("x")[0]))
			xvals = [x["scale"] for x in filtered_data]
			lat = [x["latency"] for x in filtered_data]
			bs_lat = [x["bs_latency"] for x in filtered_data]
			tp = [x["throughput"] for x in filtered_data]
			bs_tp = [x["bs_throughput"] for x in filtered_data]
			lat_rt = [x["runtime_lat"] for x in filtered_data]
			bs_lat_rt = [x["bs_runtime_lat"] for x in filtered_data]
			tp_rt = [x["runtime_tp"] for x in filtered_data]
			bs_tp_rt = [x["bs_runtime_tp"] for x in filtered_data]
			#print("RC-Lat-Runtime for %s and %s: From %.2f to %.2f" % (topology, traffic, min(lat_rt), max(lat_rt)))
			#print("BS-TP-Runtime for %s and %s: From %.2f to %.2f" % (topology, traffic, min(bs_lat_rt), max(bs_lat_rt)))
			#print("RC-Lat-Runtime for %s and %s: From %.2f to %.2f" % (topology, traffic, min(tp_rt), max(tp_rt)))
			print("BS-TP-Runtime for %s and %s: From %.2f to %.2f" % (topology, traffic, min(bs_tp_rt), max(bs_tp_rt)))

			metrics = [lat, bs_lat, tp, bs_tp, lat_rt, bs_lat_rt, tp_rt, bs_tp_rt]
			for (k, metric) in enumerate(metrics):
				ax[k][i].plot(xvals, metric, label=topology, marker=markers[j], color=colors[j])
				limits[k][0] = min(limits[k][0], min(metric))
				limits[k][1] = max(limits[k][1], max(metric))
				values[k][1].append(sum([abs(x) for x in metric]) / len(metric))
				# Add a horizontal line at 0 for the error plots
				if k % 2 == 0:
					ax[k][i].axhline(0, color="black", linestyle="--")
	# Y-labels
	ax[0][0].set_ylabel("Latency [cycles]")
	ax[1][0].set_ylabel("BookSim Latency [cycles]")
	ax[2][0].set_ylabel("Throughput [flits/cycle]")
	ax[3][0].set_ylabel("BookSim Throughput [flits/cycle]")
	ax[4][0].set_ylabel("Latency Runtime [s]")
	ax[5][0].set_ylabel("BookSim Latency Runtime [s]")
	ax[6][0].set_ylabel("Throughput Runtime [s]")	
	ax[7][0].set_ylabel("BookSim Throughput Runtime [s]")
	# General y-axis settings
	for (i, limit) in enumerate(limits):
		lmt = max(limits[2 * (i//2)][1], abs(limits[2 * (i//2)+1][1])) if i < 4 else limits[i][1]
		for (j, traffic) in enumerate(traffics):
			# Y-Limit
			ax[i][j].set_ylim(0, lmt)
			# Grid
			ax[i][j].grid(which="both")
			ax[i][j].set_yticks(ax[i][j].get_yticks()[1:-1])
			# Only show Y-Tick labels on the left-most subplots
			if j > 0:
				ax[i][j].set_yticklabels([])
	# General x-axis settings
	for i in range(8):
		for j in range(len(traffics)):
			ax[i][j].set_xticks(range(len(scales)))
			if i == 7:	
				ax[i][j].set_xlabel("Number of Chiplets")
				ax[i][j].set_xticklabels(scales, rotation=90)
			else:
				ax[i][j].set_xticklabels([])
	# Save the plot
	plt.savefig("plots/extended_evaluation.pdf")
	# Print the average values
	for (name, values) in values:
		print("Average %s: %.3f %s" % (name, sum(values) / len(values), "%" if "Error" in name else ""))

def create_case_study_plot():
	data = []
	# Read all files in the results directory
	for file in os.listdir("results"):
		if file.startswith("case_study") and file.endswith(".json"):
			results = hlp.read_json("results/%s" % file)
			lat = results["latency"]["avg"]
			tp = results["throughput"]["aggregate_throughput"] * 1e-3	# bits/cycle to kbits/cycle
			area = results["area_summary"]["total_chiplet_area"] * 1e-2	# mm^2 to cm^2
			config = file.split(".")[0].split("-")[1:]
			entry = {"latency": lat, "throughput": tp, "area": area, "config": config}
			data.append(entry)
	print("Total number of points: %d" % len(data))
	# Remove duplicates and close-to-duplicates since 65k points leads to a too large PDF
	unique_points = []
	filtered_data = []
	for entry in data:
		lat = round(entry["latency"], 0)
		tp = round(entry["throughput"], 0)
		area = round(entry["area"], 1)
		point = (lat, tp, area)
		if point not in unique_points:
			unique_points.append(point)
			filtered_data.append(entry)
	print("Number of unique points: %d" % len(filtered_data))
	data = filtered_data
	# Create the plot
	(fig, ax) = plt.subplots(1, 1, figsize=(5, 3))
	fig.subplots_adjust(left=0.125, right=0.975, top=0.975, bottom=0.15)
	# Plot the data
	lats = [x["latency"] for x in data]
	tps = [x["throughput"] for x in data]	
	areas = [x["area"] for x in data]	
	cmap = ax.scatter(lats, tps, c=areas, s=0.5, marker = "o", cmap = "RdYlGn_r", zorder=3).get_cmap()
	(min_area,max_area) = (min(areas), max(areas))
	# Plot specific configurations
	mesh = None
	flattened_bf = None
	for x in data:
		if x["config"] == ["_","_"]:
			mesh = x
		elif x["config"] == ["2_3_4_5_6_7_8_9","2_3_4_5_6_7_8_9"]:
			flattened_bf = x
	col = cmap((mesh["area"] - min_area) / (max_area - min_area))
	ax.scatter(mesh["latency"], mesh["throughput"], s=15, marker = "*", zorder=4, color = col)
	col = cmap((flattened_bf["area"] - min_area) / (max_area - min_area))
	ax.scatter(flattened_bf["latency"], flattened_bf["throughput"], s=15, marker = "*", zorder=4, color = col)
	# Identify and draw different Pareto-frontiers for different area-overheads
	for overhead in range(16,-1,-2):
		area_limit = min_area * (1 + overhead / 100)
		valid_data = [x for x in data if x["area"] <= area_limit]
		pareto_points = []
		for entry in valid_data:
			is_pareto = True
			for other in valid_data:
				if other["latency"] < entry["latency"] and other["throughput"] > entry["throughput"]:
					is_pareto = False
					break
			if is_pareto:
				pareto_points.append(entry)
		pareto_points = sorted(pareto_points, key=lambda x: x["latency"])
		col = cmap((area_limit - min_area) / (max_area - min_area))
		(lats, tps) = ([x["latency"] for x in pareto_points], [x["throughput"] for x in pareto_points])
		ax.plot(lats, tps, color = col, zorder = 5, linewidth = 2)
		ax.plot(lats, tps, color = "#000000", zorder = 5, linewidth = 0.25)
	# Add grid and background
	ax.set_facecolor("#CCCCCC")
	ax.grid(which="both", color = "#666666", zorder=0)
	# Add color bar
	cbar = plt.colorbar(ax.collections[0], ax=ax)
	# Axis
	ax.set_xlabel("Latency [cycles]")
	ax.set_ylabel("Aggregate Throughput [kbits/cycle]")
	ax.text(241, 130, r"Total Area [cm$^2$]", ha="center", va="center", rotation=90)
	# Save the plot	
	plt.savefig("plots/case_study.pdf")

if __name__ == "__main__":
	# Evaluation Plot (Fig 4 in the paper)
	create_evaluation_plot()
	# Extended Evaluation Plot showing the absolute latency and throughput values and the runtimes (not in the paper)
	create_extended_evaluation_plot()
	# Case Study Plot (Fig 5 in the paper)
	create_case_study_plot()

