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
from lib.config import read_config
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions, get_model_configs, get_prompt_variants

# load env
config = read_config()

# load ai eval spreadsheet
ai_eval_sheet = read_ai_eval_spreadsheet()

results = ai_eval_sheet.evaluation_results.data.df.copy()

# use polars
results = pl.DataFrame(results)

results.columns

# rename the prompt_variation_id to match our report
results.select(pl.col(['prompt_variation_id']).unique())


prompt_id_mapping = {
    'instruct_question_options_1': 'prompt1',
    'instruct_question_options_2': 'prompt3',
    'no_option_letter': 'prompt2',
    'zh_no_option_letter': 'prompt2',
    'zh_instruct_2': 'prompt3',
    'zh_instruct_1': 'prompt1'
}

results = results.with_columns(
    pl.col('prompt_variation_id').replace(prompt_id_mapping)
)

# double check
results['prompt_variation_id'].unique()

# create a mapping for model_id -> the actual brand, name and parameters
model_configs = get_model_configs(ai_eval_sheet, include_all=True)


def search_model(model_config_id):
    for model, model_config in model_configs:
        if model_config.model_config_id == model_config_id:
            return ' '.join([
                model.vendor, model.model_name, model_config.model_parameters])
    raise ValueError(f'{model_config_id} not found!')


model_config_ids = results['model_configuration_id'].unique().to_list()
model_config_names = [search_model(x) for x in model_config_ids]
model_config_id_mapping = dict(zip(model_config_ids, model_config_names))


# replace nan to indecisive in result
results = results.with_columns(
    pl.col('result').replace({'nan': 'indecisive'})
)

# double check
results['model_configuration_id'].unique()


# Table 1. The number of different answers by model and prompt
table1 = results.with_columns(
    pl.concat_list(pl.col([
        'percent_correct',
        'percent_wrong',
        'percent_very_wrong',
        'percent_eval_failed'])).alias('tmp')
).with_columns(
    pl.col('tmp').map_elements(
        lambda x: len(list(filter(lambda e: e != 0, x)))
    ).alias('number_of_answers')
).select(
    pl.exclude('tmp')
).group_by(['model_configuration_id', 'prompt_variation_id']).agg(
    pl.col('number_of_answers').mean()
)

table1 = table1.with_columns(
    pl.col('model_configuration_id').replace(model_config_id_mapping).alias('model_name')
)

table1

table1.write_csv('../output/report_tables/1_number_of_average_answers.csv')

# Table 2. Correct / Wrong / Very Wrong / Indecisive Rates
table2 = results.group_by(
    ['model_configuration_id', 'prompt_variation_id']
).agg(
    pl.col('result').count().alias('total_questions_asked'),
    (pl.col('result').filter(pl.col('result') == 'correct').count()
     / pl.col('result').count()
     * 100).alias("Correct Rate %"),
    (pl.col('result').filter(pl.col('result') == 'wrong').count()
     / pl.col('result').count()
     * 100).alias("Wrong Rate %"),
    (pl.col('result').filter(pl.col('result') == 'very_wrong').count()
     / pl.col('result').count()
     * 100).alias("Very Wrong Rate %"),
    (pl.col('result').filter(pl.col('result').is_in(['indecisive', 'fail'])).count()
     / pl.col('result').count()
     * 100).alias("Indecisive Rate %")
)

# double check
table2.with_columns(
    (pl.col('Correct Rate %') +
     pl.col('Wrong Rate %') +
     pl.col('Very Wrong Rate %') +
     pl.col('Indecisive Rate %')).alias('total')
)['total'].min()  # should be about 100

table2 = table2.with_columns(
    pl.col('model_configuration_id').replace(model_config_id_mapping).alias('model_name')
)

table2

table2.write_csv('../output/report_tables/2_average_rates.csv')


# Table 3. correct rate by prompt
# don't use 20231104 result in this table. Because in that experiment
# we didn't test prompt3.
table3 = results.filter(
    ~pl.col('last_evaluation_datetime').is_in(['20231104'])
).group_by(
    ['prompt_variation_id']
).agg(
    pl.col('result').count().alias('total_questions_asked'),
    (pl.col('result').filter(pl.col('result') == 'correct').count()
     / pl.col('result').count()
     * 100).alias("Correct Rate %"),
    (pl.col('result').filter(pl.col('result') == 'wrong').count()
     / pl.col('result').count()
     * 100).alias("Wrong Rate %"),
    (pl.col('result').filter(pl.col('result') == 'very_wrong').count()
     / pl.col('result').count()
     * 100).alias("Very Wrong Rate %"),
    (pl.col('result').filter(pl.col('result').is_in(['indecisive', 'fail'])).count()
     / pl.col('result').count()
     * 100).alias("Indecisive Rate %")
)

table3

table3.write_csv('../output/report_tables/3_correct_rate_by_prompt.csv')
