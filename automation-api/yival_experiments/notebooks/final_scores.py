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
# also read the last experiment
results1 = pd.read_excel('../output/archives/20231104/results.xlsx')
results2 = pd.read_excel('../output/results.xlsx')

# concat them
output_df = pd.concat([results1, results2], ignore_index=True)

output_df


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

output_df.columns

output_df.model_id.unique()

# table 1. how many answers, per question and model?
df = pl.DataFrame(output_df)

# df.group_by(['question_id', 'model_id', 'model_params', 'prompt_template']).agg(
#     pl.col('correctness').count()
# )['correctness'].max()

model_answers = df.group_by(['question_id', 'model_id', 'model_params', 'prompt_template']).agg(
    pl.col('correctness').unique().count()
).group_by(['model_id', 'model_params', 'prompt_template']).agg(
    pl.col('correctness').mean()
)
model_answers.write_csv('../output/answer_num.csv')


model_correctness = output_df.groupby(["question_id", "model_id", "model_params"])[
    "correctness"
].apply(lambda x: correctness(x.values))


# let's use polars. The syntax is easier than pandas
model_correctness = pl.DataFrame(model_correctness.reset_index())

# ## correct rate by model

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

# ## correct rates by prompts and model

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

# ## correct rates break down by prompt.

prompt_templates = output_df['prompt_template'].unique()

prompt_templates.tolist()

# NOTE:
# if you encounter error in the cell below:
# output_df['prompt_id'] = output_df['prompt_template'].map(lambda x: prompt_id_mappings[x])
# please copy the output of above cell, and replace the list below with it.
prompt_templates_lst = [
    "Please answer this multiple choices question. If you can't determine the answer please make your best guess:\n\nQuestion:\n{question_text}\nA. {option_a}\nB. {option_b}\nC. {option_c}\n\nAnswer:",
    "Pick the correct answer: A, B or C. If you can't determine the answer please make your best guess.\n\nQuestion:\n{question_text}\nA. {option_a}\nB. {option_b}\nC. {option_c}\n\nAnswer:",
    'Question:\n{question_text}\nIs it: {option_a};  {option_b}; or {option_c}? \n\nAnswer:',
    '请回答以下单选题。如果你不知道哪个答案正确，请回答你认为最接近的答案。\n 问题：\n{question_text}\nA. {option_a}\nB. {option_b}\nC. {option_c}\n 答案：\n',
    '以下单选题，请你从 A，B，C 中选择一个正确的答案。如果你不知道哪个答案正确，请回答你认为最接近的答案。\n 问题：\n{question_text}\nA. {option_a}\nB. {option_b}\nC. {option_c}\n 答案：\n',
    '问题：\n{question_text}\n 是 {option_a}，{option_b}，还是 {option_c}？\n 答案：\n'
]

prompt_id_mappings = dict(
    zip(prompt_templates_lst, ['prompt1',
                               'prompt3',
                               'prompt2',
                               'prompt1',
                               'prompt3',
                               'prompt2'])
)

prompt_id_mappings

output_df['prompt_id'] = output_df['prompt_template'].map(lambda x: prompt_id_mappings[x])

prompt_correctness = output_df.groupby(
    ["question_id", "prompt_id"]
)["correctness"].apply(lambda x: correctness(x.values))


prompt_correctness = pl.DataFrame(prompt_correctness.reset_index())

prompt_correctness

out1 = prompt_correctness.group_by(['prompt_id']).agg(
    pl.col("correctness").filter(pl.col("correctness") == 3).count()
    / pl.col("correctness").count()
    * 100
).select(
    pl.col(['prompt_id']),
    pl.col('correctness').alias("correct_rate_with_indecisive")
)

out1

out1.write_csv('../output/correct_rate_with_indecisive_by_prompt.csv')


out2 = (
    prompt_correctness
    .filter(pl.col("correctness") != 0)
    .group_by(['prompt_id'])
    .agg(
        pl.col("correctness").filter(pl.col("correctness") == 3).count()
        / pl.col("correctness").count()
        * 100
    )
).select(
    pl.col(['prompt_id']),
    pl.col('correctness').alias("correct_rate_without_indecisive")
)

out2

out2.write_csv('../output/correct_rate_without_indecisive_by_prompt.csv')
