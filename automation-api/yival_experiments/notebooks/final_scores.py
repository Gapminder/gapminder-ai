# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: gapminder-ai-automation-api
#     language: python
#     name: gapminder-ai-automation-api
# ---

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


# +
# output_df.columns
# for g, df in output_df.groupby(['question_id', 'model_id', 'model_params']):
#     print(g)
#     print(is_correct_p(df['correctness'].values))
# -


model_correctness = output_df.groupby(["question_id", "model_id", "model_params"])[
    "correctness"
].apply(lambda x: correctness(x.values))


# let's use polars. The syntax is easier than pandas
model_correctness = pl.DataFrame(model_correctness.reset_index())

# calculate model correctness
# TODO: I think it's possible to convert these into a Yival Evaluator.
# 1. the correct rate for all answers
out1 = (
    model_correctness.group_by(["model_id", "model_params"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
).select(
    pl.col(['model_id', 'model_params']),
    pl.col('correctness').alias("correct_rate_with_indecisive")
)

out1

out1.write_csv('../output/correct_rate_with_indecisive.csv')

# 2. the correct rate when excluding all cases where correctness == 0
out2 = (
    model_correctness.filter(pl.col("correctness") != 0)
    .group_by(["model_id", "model_params"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
).select(
    pl.col(['model_id', 'model_params']),
    pl.col('correctness').alias("correct_rate_without_indecisive")
)

out2

out2.write_csv('../output/correct_rate_without_indecisive.csv')

# 3. the respond rate: (count correctness!=0) / (count total answers)
out3 = (
    model_correctness
    .group_by(["model_id", "model_params"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") != 0).count()
        / pl.col("correctness").count()
        * 100
    )
).select(
    pl.col(['model_id', 'model_params']),
    pl.col('correctness').alias('response_rate')
).sort("response_rate", descending=True)

out3

out3.write_csv('../output/response_rate.csv')

# break down the score by prompts
model_correctness_prompt = output_df.groupby(
    ["question_id", "model_id", "model_params", "prompt_template"]
)["correctness"].apply(lambda x: correctness(x.values))

model_correctness_prompt = pl.DataFrame(model_correctness_prompt.reset_index())

model_correctness_prompt

out1 = (
    model_correctness_prompt.group_by(["model_id", "model_params", "prompt_template"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
).select(
    pl.col(['model_id', 'model_params', 'prompt_template']),
    pl.col('correctness').alias("correct_rate_with_indecisive")
)

out1

out1.write_csv('../output/correct_rate_with_indecisive_prompt.csv')


out2 = (
    model_correctness_prompt.filter(pl.col("correctness") != 0)
    .group_by(["model_id", "model_params", "prompt_template"])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
    .sort("correctness", descending=True)
).select(
    pl.col(['model_id', 'model_params', 'prompt_template']),
    pl.col('correctness').alias("correct_rate_without_indecisive")
)

out2

out2.write_csv('../output/correct_rate_without_indecisive_prompt.csv')

out3 = (
    model_correctness_prompt
    .group_by(["model_id", "model_params", 'prompt_template'])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") != 0).count()
        / pl.col("correctness").count()
        * 100
    )
).select(
    pl.col(['model_id', 'model_params', 'prompt_template']),
    pl.col('correctness').alias('response_rate')
).sort("response_rate", descending=True)

out3

out3.write_csv('../output/response_rate_prompt.csv')
