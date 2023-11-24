# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: gapminder-ai-automation-api
#     language: python
#     name: gapminder-ai-automation-api
# ---

"""A script to create and upload result table to AI Eval Spreadsheet.
"""

import re
import json
import numpy as np
import pandas as pd
import polars as pl
from datetime import datetime
from langdetect import detect
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions, get_model_configs, get_prompt_variants
from lib.config import read_config

# load env
read_config()


raw_results = pd.read_excel('../output/results.xlsx')

raw_results

# load AI Eval Spreadsheet
ai_eval_sheet = read_ai_eval_spreadsheet()

# create a mapping from question text -> question_id + language pair.
questions = get_questions(ai_eval_sheet, include_all=True)


# Possible Issue: the question is gone in Ai Eval spreadsheet, but it's there when we
# ran the experiment.
# so here is a function to detect if an input string is English or Chinese
def suggest_language(q_text):
    lang = detect(q_text)
    if lang == 'en':
        return 'en-US'
    else:
        return 'zh-CN'

q_text_to_q_id_mapping = {}

for _, row in raw_results[['question_id', 'question']].drop_duplicates().iterrows():
    q_text = row['question']
    q_id = row['question_id']
    for q, _ in questions:
        if q_text.strip() == q.published_version_of_question.strip():
            q_text_to_q_id_mapping[q_text] = (q.question_id, q.language)
            break
    else:
        print(q_id, q_text[:10], '...')
        lang = suggest_language(q_text)
        print(lang)
        q_text_to_q_id_mapping[q_text] = (q_id, lang)

# q_text_to_q_id_mapping
# len(q_text_to_q_id_mapping)

# create a mapping from model_id, parameters -> model_config id
model_configs = get_model_configs(ai_eval_sheet, include_all=False)

model_id_params_to_model_config_mapping = {}

for model_id, params in raw_results[['model_id', 'model_params']].drop_duplicates().values:
    for model, conf in model_configs:
        if model.model_id == model_id and params == str(json.loads(conf.model_parameters)):
            model_id_params_to_model_config_mapping[(model_id, params)] = conf.model_config_id
            break
    else:
         print(model_id, params, "not found")


# model_id_params_to_model_config_mapping

# create a mapping from prompt_variant_text -> prompt_variant_id
prompt_variants = get_prompt_variants(ai_eval_sheet, include_all=True)

prompt_text_to_prompt_id_mapping = {}

for prompt_text in raw_results['prompt_template'].unique():
    for prompt in prompt_variants:
        try:
            prompt_full = prompt.question_prompt_template.format(question=prompt.question_template)
        except KeyError:
            # ignore when the prompt template need more than the question to format.
            continue
        if prompt_text == prompt_full:
            prompt_text_to_prompt_id_mapping[prompt_text] = prompt.variation_id
            break

# prompt_text_to_prompt_id_mapping

# convert the raw result to a dataframe with labelled data.
result = raw_results.copy()

# convert to question id.
result['language'] = result['question'].map(lambda x: q_text_to_q_id_mapping[x][1])

# convert to prompt variant id
result['prompt_variant_id'] = result['prompt_template'].map(lambda x: prompt_text_to_prompt_id_mapping[x])

# convert to model_conf_id
result['model_conf_id'] = [model_id_params_to_model_config_mapping[
    (row['model_id'], row['model_params'])] for _, row in result.iterrows()]

# counting
# let's use polars from now
result = pl.DataFrame(result)
result

# result.group_by(
#     ['question_id', 'language', 'prompt_variant_id', 'model_conf_id']
# ).agg(
#     pl.col('correctness').value_counts()
# )

result_counts = result.group_by(
    ['question_id', 'language', 'prompt_variant_id', 'model_conf_id']
).agg(
    pl.col('correctness').filter(pl.col('correctness') == 0).count().alias('fail'),
    pl.col('correctness').filter(pl.col('correctness') == 1).count().alias('very_wrong'),
    pl.col('correctness').filter(pl.col('correctness') == 2).count().alias('wrong'),
    pl.col('correctness').filter(pl.col('correctness') == 3).count().alias('correct'),
)

result_pct = result_counts.with_columns(
    pl.col('fail') / 5 * 100,
    pl.col('very_wrong') / 5 * 100,
    pl.col('wrong') / 5 * 100,
    pl.col('correct') / 5 * 100,
)

# calculate the final grade
def get_grade(dictionary):
    max_value = max(dictionary.values())
    max_keys = [key for key, value in dictionary.items() if value == max_value]

    if len(max_keys) > 1:
        return "n/a"
    else:
        return max_keys[0]

# FIXME: remove date from result
date = datetime(2023, 11, 4)

result_full = result_pct.with_columns(
    pl.struct(pl.col(['fail', 'very_wrong', 'wrong', 'correct'])).map_elements(get_grade).alias('result'),
    pl.lit(5).alias('rounds'),
    pl.lit(date).alias('last_evaluation')
)

result_full

result_full_df = result_full.to_pandas()
result_full_df.columns

result_full_df.columns = ['question_id', 'language', 'prompt_variation_id',
                          'model_configuration_id', 'percent_eval_failed', 'percent_very_wrong', 'percent_wrong',
                          'percent_correct', 'result', 'rounds', 'last_evaluation_datetime']

backup = ai_eval_sheet.evaluation_results.data.df.copy()

backup.columns

result_full_df = result_full_df[backup.columns]

ai_eval_sheet.evaluation_results.replace_data(result_full_df)
