# Python modules 
import copy as cpy
import argparse


# RapidChiplet modules
import helpers as hlp
import generate_inputs as igen
import rapidchiplet as rc


def split_parameters(experiment):
	# Divide parameters into fixed ones and ones where we iterate over a range
	base_params = {}
	ranged_params = {}
	for param in experiment:
		if len(experiment[param]) > 1:
			ranged_params[param] = experiment[param]
		elif len(experiment[param]) == 1:
			base_params[param] = experiment[param][0]
		else:
			# We assume that the given parameter is not used for the configured experiment
			# If this is not the case, the function generate_inputs() will fail and the user
			# will be able to identify the issue and add the missing parameter to the experiment file
			pass
	return (base_params, ranged_params)


def compute_parameter_combinations(experiment, exp_name):
	(base_params, ranged_params) = split_parameters(experiment)
	# Create a list of all possible combinations of the ranged parameters (all single experiments)
	# NOTE: The number of experiments can grow exponentially 
	experiments = {exp_name : base_params}
	range_param_idx = 0
	for (ranged_param_name, ranged_param_values) in ranged_params.items():
		new_experiments = {}
		for (exp_name, exp_params) in experiments.items():
			for ranged_param_value in ranged_param_values:
				suffix = ("_".join([str(x) for x in ranged_param_value]) if type(ranged_param_value) == list else str(ranged_param_value))
				suffix = "_" if suffix == "" else suffix
				new_exp_name = exp_name + "-" + suffix
				new_exp_params = cpy.deepcopy(exp_params)
				new_exp_params[ranged_param_name] = ranged_param_value
				new_experiments[new_exp_name] = new_exp_params
		experiments = new_experiments
	return experiments


def run_single_configuration(params, metrics_to_compute, exp_name):
	# Generate the experiment setup
	inputs = igen.generate_inputs(params, exp_name, do_write = False)
	# Arguments for the rapidchiplet function
	intermediates = {}
	do_compute = {metric : (metric in metrics_to_compute) for metric in rc.metrics}
	results_file = exp_name
	# Run RapidChiplet
	results = rc.rapidchiplet(inputs, intermediates, do_compute, results_file, verbose = True, validate = params["do_validate"])
	# Save the results
	hlp.write_json("./results/%s.json" % exp_name, results)


def run_experiment(experiment):
	# Extract the experiment name and metrics to compute
	exp_name = experiment["exp_name"]
	metrics_to_compute = experiment["metrics"]
	del experiment["exp_name"]
	del experiment["metrics"]
	experiments = compute_parameter_combinations(experiment, exp_name)
	n_exp = len(experiments)
	# Run all experiments
	for (idx, new_exp_name) in enumerate(experiments):
		print("=" * 100)
		print("Running experiment %d/%d: %s" % (idx + 1, n_exp, new_exp_name))
		print("=" * 100)
		run_single_configuration(experiments[new_exp_name], metrics_to_compute, new_exp_name)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-e", "--experiment", required=True, help="Path to the \"experiment\" input file")
	args = parser.parse_args()
	# Load the experiment file
	experiment = hlp.read_json(args.experiment)
	# Run the experiment
	run_experiment(experiment)
				
			
	
	
	
	

