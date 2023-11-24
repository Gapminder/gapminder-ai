# calculate final scores for models

# import libs
from collections import Counter
import polars as pl
import pandas as pd


# read the raw responses
output_df = pd.read_excel('../output/results.xlsx')


# function to check if the model answered correctly considering all responses.
# it's correct when the most common answer in all responses is correct.
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

# model correctness
# TODO: I think it's possible to convert these into a Yival Evaluator.
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
