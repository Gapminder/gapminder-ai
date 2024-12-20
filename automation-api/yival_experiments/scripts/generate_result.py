import os.path as osp
import pickle
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
from yival.experiment.experiment_runner import Experiment

current_script_path = Path(__file__).parent

# all Yival experiment results are exported into pickle files.
# you can use follow code to explore the structure.
# change fp variable to the pickle file path
# fp = "path/to/result.pkl"
# data: Experiment = pickle.load(open(fp, "rb"))
# data.group_experiment_results[0].asdict()
# result = data.group_experiment_results[1]
# rs = result.experiment_results
# len(rs)
# rs[1].asdict()

# We will combine all pickle files in output dir and calculate final scores.
# In this script, we store all responses into an excel file.
output_dir = current_script_path / "../output"

option_score_mapping = {"Correct": 3, "Wrong": 2, "Very Wrong": 1}


def exact_match_correctness(answer, options, correctness):
    option_occurance = [0, 0, 0]
    scores = [option_score_mapping[x] for x in correctness]
    for i, o in zip(range(3), options):
        if o.strip().lower() in answer.strip().lower():
            option_occurance[i] = 1
    if sum(option_occurance) == 1:
        score = scores[option_occurance.index(1)]
    else:
        score = 0

    return score


def extract_correct_answer(options, correctness):
    for t, c in zip(options, correctness):
        if c == "Correct":
            return t


if __name__ == "__main__":
    output_list = []

    for fp in glob(f"{output_dir}/*.pkl"):
        # Note: we assumed that the filenames are begging with "experiment_${date}_"
        # so that we can extract the date from result files.
        expr_date = osp.basename(fp).split("_")[1][:8]
        data: Experiment = pickle.load(open(fp, "rb"))
        for group_results in data.group_experiment_results:
            for result in group_results.experiment_results:
                row = result.input_data.content
                answer = result.raw_output.text_output
                option_a = row["option_a"]
                option_b = row["option_b"]
                option_c = row["option_c"]
                option_a_correctness = row["option_a_correctness"]
                option_b_correctness = row["option_b_correctness"]
                option_c_correctness = row["option_c_correctness"]
                options = [option_a, option_b, option_c]
                correctness = [
                    option_a_correctness,
                    option_b_correctness,
                    option_c_correctness,
                ]
                auto_mark_correctness = exact_match_correctness(
                    answer, options, correctness
                )
                correct_answer = extract_correct_answer(options, correctness)
                result_dict = dict(
                    experiment_date=expr_date,
                    question_id=str(result.input_data.content["question_id"]),
                    model_id=result.combination["model_config"]["model_id"],
                    model_params=str(result.combination["model_config"]["params"]),
                    prompt_template=result.combination["prompt_template"],
                    question=result.input_data.content["question_text"],
                    raw_output=result.raw_output.text_output,
                    correct_answer=correct_answer,
                    auto_mark_correctness=auto_mark_correctness,
                )
                for eval_output in result.evaluator_outputs:
                    col_name = f"{eval_output.name}_{eval_output.display_name}"
                    result_dict[col_name] = eval_output.result

                output_list.append(result_dict)

    output_df = pd.DataFrame.from_records(output_list)
    # add a human rating column
    output_df["human_rating_score"] = np.nan
    output_df.to_excel(osp.join(output_dir, "results.xlsx"), index=False)
    output_df.to_parquet(osp.join(output_dir, "results.parquet"), index=False)

    print("done")
