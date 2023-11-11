from glob import glob
import pandas as pd
import pickle
from collections import Counter
import polars as pl

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
# TODO: follow the format in `Latest Results` sheet of AI eval spreadsheet
# 1. Store all responses into excel file.
output_list = []

for fp in glob("./*.pkl"):
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

output_df.to_excel("./results.xlsx", index=False)


# 2. calculate a final score per model configuration
# TODO: I think it's possible to convert these into a Yival Evaluator.
def is_correct_p(round_results):
    c = Counter(round_results)
    top2 = c.most_common(2)
    if len(top2) == 1:
        if top2[0][0] == 3:
            return True
        else:
            return False
    else:
        if top2[0][1] != top2[1][1] and top2[0][0] == 3:
            return True
        else:
            return False


def correctness(lst):
    c = Counter(lst)
    top2 = c.most_common(2)

    if len(top2) > 1 and top2[0][1] == top2[1][1]:
        return 0

    return top2[0][0]


# output_df.columns
# for g, df in output_df.groupby(['question_id', 'model_id', 'model_params']):
#     print(g)
#     print(is_correct_p(df['correctness'].values))


model_correctness = output_df.groupby(["question_id", "model_id", "model_params"])[
    "correctness"
].apply(lambda x: correctness(x.values))

# let's use polars. The syntax is easier than pandas
model_correctness = pl.DataFrame(model_correctness.reset_index())
# model_correctness

out1 = (
    model_correctness.group_by(["model_id", "model_params"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
)

out2 = (
    model_correctness.filter(pl.col("correctness") != 0)
    .group_by(["model_id", "model_params"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
)

out1.join(out2, on=["model_id", "model_params"]).select(
    pl.col(["model_id", "model_params"]),
    pl.col("correctness").alias("correctness_with_indecisive"),
    pl.col("correctness_right").alias("correctness_without_indecisive"),
).sort("correctness_without_indecisive", descending=True).write_csv("result_comb.csv")


# break down the score by prompts
model_correctness = output_df.groupby(
    ["question_id", "model_id", "model_params", "prompt_template"]
)["correctness"].apply(lambda x: correctness(x.values))

model_correctness = pl.DataFrame(model_correctness.reset_index())
# model_correctness

out1 = (
    model_correctness.group_by(["model_id", "model_params", "prompt_template"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
)


out2 = (
    model_correctness.filter(pl.col("correctness") != 0)
    .group_by(["model_id", "model_params", "prompt_template"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
)

out1.join(out2, on=["model_id", "model_params", "prompt_template"]).select(
    pl.col(["model_id", "model_params", "prompt_template"]),
    pl.col("correctness").alias("correctness_with_indecisive"),
    pl.col("correctness_right").alias("correctness_without_indecisive"),
).sort("correctness_without_indecisive", descending=True).write_csv(
    "result_comb_prompt.csv"
)

print("done")
