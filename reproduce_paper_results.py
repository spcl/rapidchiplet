# Python modules
import sys

# RapidChiplet modules
import helpers as hlp
import create_paper_plots as cpp
import create_plots as cp
import visualizer as vis
import run_experiment as re
import rapidchiplet as rc
import case_study as cs

def reproduce_paper_results():
	##################################################	
	# Visualization 
	##################################################	
	# Load the design
	design = hlp.read_json("inputs/designs/example_design.json")
	# Run RapidChiplet
	inputs = {"design" : design}
	intermediates = {}
	do_compute = {"latency" : True, "throughput" : True, "area_summary" : True, "power_summary" : True, "link_summary" : True, "cost" : True, "booksim_simulation" : True}
	results_file = "example_design.json"
	results = rc.rapidchiplet(inputs, intermediates, do_compute, results_file, verbose = False, validate = True)
	# Save and read the results (hack to fix formatting)
	hlp.write_json("./results/example_design.json", results)
	results = hlp.read_json("./results/example_design.json")
	# Visualize the design
	inputs = {"design":design,"verbose":True,"validate":True}
	vis.visualize_design(inputs, "example_design", show_chiplet_id = True, show_phy_id = False)
	# Create the latency-vs-load plot
	cp.create_latency_vs_load_plot(results)
	##################################################	
	# Evaluation
	##################################################	
	# Load experiments for the evaluation
	experiment_lat = hlp.read_json("experiments/evaluation_latency.json")
	experiment_tp = hlp.read_json("experiments/evaluation_throughput.json")
	experiment_link = hlp.read_json("experiments/evaluation_links.json")
	experiment_bs = hlp.read_json("experiments/evaluation_booksim.json")
	# Run the experiment
	re.run_experiment(experiment_lat)
	re.run_experiment(experiment_tp)
	re.run_experiment(experiment_link)
	re.run_experiment(experiment_bs)
	# Create the evaluation plot for the paper and the extended evaluation plot
	cpp.create_evaluation_plot()
	cpp.create_extended_evaluation_plot()
	##################################################
	# Case study
	##################################################
	cs.case_study()
	cpp.create_case_study_plot()

if __name__ == "__main__":
	reproduce_paper_results()

