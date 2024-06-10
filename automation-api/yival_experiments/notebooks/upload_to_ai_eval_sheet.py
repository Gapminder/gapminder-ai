# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.2
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
import yaml
from datetime import datetime
from langdetect import detect
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions, get_model_configs, get_prompt_variants
from lib.config import read_config

# load env
config = read_config()

raw_results = pd.read_excel('../output/results.xlsx')
# also, save it as parquet, for easier loading into other tools
# raw_results.to_parquet('../notebooks/data/raw_results_experiment_3.parquet')

# set question_id field to string
raw_results['question_id'] = raw_results['question_id'].astype(str)

raw_results

# load AI Eval Spreadsheet
ai_eval_sheet = read_ai_eval_spreadsheet()

# create a mapping from question text -> question_id + language pair.
questions = get_questions(ai_eval_sheet, include_all=True)


# Possible Issue: the question is gone or changed in Ai Eval spreadsheet
# so we need to detect the language if we can't find that question.
# Here is a function to detect if an input string is English or Chinese
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
    matched = False
    for q, _ in questions:
        if q_id == q.question_id:
            if q_text.strip() == q.published_version_of_question.strip():
                matched = True
                q_text_to_q_id_mapping[q_text] = (q.question_id, q.language)
            else:
                lang = suggest_language(q_text)
                if lang == q.language:
                    matched = True
                    q_text_to_q_id_mapping[q_text] = (q.question_id, q.language)
                    print(f"Q{q_id} have different question text.")
                    print(q_text.strip())
                    print(q.published_version_of_question.strip())
        if matched:
            break

    if not matched:
        lang = suggest_language(q_text)
        print(q_id, q_text[:10], '...', 'does not exist, detected lang:', lang)
        q_text_to_q_id_mapping[q_text] = (q_id, lang)


# q_text_to_q_id_mapping
len(q_text_to_q_id_mapping)

# double check: numbers of english questions and chinese questions
en = list(filter(lambda v: v[1] == 'en-US', q_text_to_q_id_mapping.values()))
en_ids = [x[0] for x in en]
cn = list(filter(lambda v: v[1] == 'zh-CN', q_text_to_q_id_mapping.values()))
cn_ids = [x[0] for x in cn]

# this should output an empty set
# if English question set and Chinese question set are the same.
set(en_ids) - set(cn_ids)
set(cn_ids) - set(en_ids)

# +
# fix for experiment 20231104: the gpt-4 is gpt-4-0613
raw_results.loc[raw_results['model_id'] == 'gpt-4', 'model_id'] = 'gpt-4-0613'

# fix for experiment 20240521: gpt-4o is gpt-4o-2024-05-13
raw_results.loc[raw_results['model_id'] == 'gpt-4o', 'model_id'] = 'gpt-4o-2024-05-13'
# -


# create a mapping from model_id, parameters -> model_config id
# NOTE: because we only search for model_id and parameters,
# we may found duplicates: same model_id and parameters,
# but different rounds/memory settings.
# That's why I don't include all rows here, we should manually ensure that
# the model we actually tested are enabled in the AI eval sheet.
# TODO: see if we can auto detect the correct model configuration.
model_configs = get_model_configs(ai_eval_sheet, include_all=False)


model_id_params_to_model_config_mapping = {}
for model_id, params in raw_results[['model_id', 'model_params']].drop_duplicates().values:
    matched = False
    for model, conf in model_configs:
        if model.model_id == model_id and params == str(json.loads(conf.model_parameters)):
            if matched:  # we found a duplicate
                print("duplicated rows found for model conf:",
                      model_id,
                      params)
                raise ValueError("duplicated rows")
            model_id_params_to_model_config_mapping[(model_id, params)] = conf.model_config_id
            matched = True
    if not matched:
        print(model_id,
              params,
              "not found. Please ensure it's enabled in the AI Eval Spreadsheet.")
        raise KeyError("model configuration not exist")


model_id_params_to_model_config_mapping

raise Exception("Please check if file names are correct in next cell.")

# create a mapping from prompt_variant_text -> prompt_variant_id
# to get the most accurate mapping, we will load the prompts from the experiment files
# be sure to change the name
cn_exp_config = yaml.safe_load(open('../experiment_configurations/experiment_202405162248_qwen-max-0403_zh-CN.yaml', 'r'))
en_exp_config = yaml.safe_load(open('../experiment_configurations/experiment_202405281300_replicate_meta_meta-llama-3-70b-instruct_en-US.yaml', 'r'))

assert cn_exp_config['variations'][1]['name'] == 'prompt_template'
assert en_exp_config['variations'][1]['name'] == 'prompt_template'

cn_prompts = pd.DataFrame.from_records(cn_exp_config['variations'][1]['variations'])
en_prompts = pd.DataFrame.from_records(en_exp_config['variations'][1]['variations'])

all_prompts = pd.concat([cn_prompts, en_prompts], ignore_index=True)

prompt_text_to_prompt_id_mapping = all_prompts.set_index('value')['variation_id'].to_dict()

prompt_text_to_prompt_id_mapping

# convert the raw result to a dataframe with labelled data.
result = raw_results.copy()

# convert to question id.
result['language'] = result['question'].map(lambda x: q_text_to_q_id_mapping[x][1])

# convert to prompt variant id
result['prompt_variant_id'] = result['prompt_template'].map(lambda x: prompt_text_to_prompt_id_mapping[x])

# convert to model_conf_id
result['model_conf_id'] = [model_id_params_to_model_config_mapping[
    (row['model_id'], row['model_params'])] for _, row in result.iterrows()]

# update the correctness column with human scores
result['final_score'] = result['human_rating_score'].fillna(result['correctness'])

# counting
# let's use polars from now
result = pl.DataFrame(result)
result

# +
# result.group_by(
#     ['question_id', 'language', 'prompt_variant_id', 'model_conf_id']
# ).agg(
#     pl.col('correctness').value_counts()
# )
# -

# FIX: In experiment on 2024-04, due to issue in prompt we tested the ideology-capitalist_zh prompt for alibaba twice.
# we will just keep one.
result = result.group_by(
    ['question_id', 'language', 'prompt_variant_id', 'model_conf_id', 'experiment_date']
).agg(pl.all().first())




result_counts = result.group_by(
    ['question_id', 'language', 'prompt_variant_id', 'model_conf_id', 'experiment_date']
).agg(
    pl.col('final_score').filter(pl.col('final_score') == 0).count().alias('fail'),
    pl.col('final_score').filter(pl.col('final_score') == 1).count().alias('very_wrong'),
    pl.col('final_score').filter(pl.col('final_score') == 2).count().alias('wrong'),
    pl.col('final_score').filter(pl.col('final_score') == 3).count().alias('correct'),
    pl.col('final_score').count().alias('rounds')
)

result_counts

result_counts['rounds'].max()


result_pct = result_counts.with_columns(
    pl.col('fail') / pl.col('rounds') * 100,
    pl.col('very_wrong') / pl.col('rounds') * 100,
    pl.col('wrong') / pl.col('rounds') * 100,
    pl.col('correct') / pl.col('rounds') * 100,
)

result_pct

# calculate the final grade
def get_grade(dictionary):
    max_value = max(dictionary.values())
    max_keys = [key for key, value in dictionary.items() if value == max_value]

    if len(max_keys) > 1:
        return "n/a"
    else:
        return max_keys[0]


result_full = result_pct.with_columns(
    pl.struct(pl.col(['fail', 'very_wrong', 'wrong', 'correct'])).map_elements(get_grade).alias('result'),
)

result_full

result_full_df = result_full.to_pandas()
result_full_df.columns

result_full_df.columns = ['question_id', 'language', 'prompt_variation_id',
                          'model_configuration_id', 'last_evaluation_datetime',
                          'percent_eval_failed', 'percent_very_wrong', 'percent_wrong',
                          'percent_correct', 'rounds', 'result']

backup = ai_eval_sheet.evaluation_results.data.df.copy()

backup.columns

result_full_df = result_full_df[backup.columns]

ai_eval_sheet.evaluation_results.replace_data(result_full_df)


