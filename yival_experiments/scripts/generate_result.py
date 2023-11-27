import os.path as osp
from glob import glob
import pandas as pd
import pickle

from yival.experiment.experiment_runner import Experiment

# all Yival experiment results are exported into pickle files.
# you can use follow code to explore the structure.
# change fp variable to the pickle file path
# fp = "gpt4_0.pkl"
# data: Experiment = pickle.load(open(fp, "rb"))
# data.group_experiment_results[:2]
# result = data.group_experiment_results[1]
# rs = result.experiment_results
# len(rs)
# rs[1].asdict()

# We will combine all pickle files in output dir and calculate final scores.
# In this script, we store all responses into an excel file.
output_dir = "../output"

if __name__ == "__main__":
    output_list = []

    for fp in glob(f"{output_dir}/*.pkl"):
        data: Experiment = pickle.load(open(fp, "rb"))
        for group_results in data.group_experiment_results:
            for result in group_results.experiment_results:
                result_dict = dict(
                    question_id=result.input_data.content["question_id"],
                    model_id=result.combination["model_config"]["model_id"],
                    model_params=str(result.combination["model_config"]["params"]),
                    prompt_template=result.combination["prompt_template"],
                    question=result.input_data.content["question_text"],
                    raw_output=result.raw_output.text_output,
                )
                for eval_output in result.evaluator_outputs:
                    result_dict[eval_output.display_name] = eval_output.result

                output_list.append(result_dict)

    output_df = pd.DataFrame.from_records(output_list)
    output_df.to_excel(osp.join(output_dir, "results.xlsx"), index=False)

    print("done")
