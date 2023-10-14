import pandas as pd
import pickle

from yival.experiment.experiment_runner import Experiment


fp = "_0.pkl"

data: Experiment = pickle.load(open(fp, "rb"))

# data.group_experiment_results
# result = data.group_experiment_results[0]
# rs = result.experiment_results
# rs[1].asdict()

output_list = []

for group_results in data.group_experiment_results:
    for result in group_results.experiment_results:
        result_dict = dict(
            combination=str(result.combination).replace("'", ""),
            question=result.input_data.content["question_text"],
            raw_output=result.raw_output.text_output,
        )
        for eval_output in result.evaluator_outputs:
            result_dict[eval_output.display_name] = eval_output.result

        output_list.append(result_dict)


output_df = pd.DataFrame.from_records(output_list)

output_df.to_csv("./results.csv", index=False)
