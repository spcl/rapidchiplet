# Import python libraries
import itertools

# Import RapidChiplet files
import helpers as hlp
import run_experiment as re

def case_study():
	# Read the experiment file
	experiment = hlp.read_json("experiments/case_study.json")
	# Construct all possible combinations of sets Sr and Sc
	rows, cols = (int(x) for x in experiment["grid_scale"][0].split("x"))
	row_options = list(range(2, rows))
	col_options = list(range(2, cols))
	row_combinations = []
	col_combinations = []
	for x in range(len(row_options) + 1):
		row_combinations.extend([list(x) for x in itertools.combinations(row_options, x)])
	for x in range(len(col_options) + 1):
		col_combinations.extend([list(x) for x in itertools.combinations(col_options, x)])
	experiment["shg_sr"] = row_combinations
	experiment["shg_sc"] = col_combinations
	# Run the experiment
	re.run_experiment(experiment)

if __name__ == '__main__':
	case_study()

