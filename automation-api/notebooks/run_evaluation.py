# Makes edits in the included files available without restarting the kernel
# %reload_ext autoreload
# %autoreload 2

# +
import logging
from datetime import datetime
from functools import partial
from collections import Counter

import pandas as pd

from lib.app_singleton import AppSingleton
from lib.pilot.helpers import (
    create_question_data_for_eval,
    create_question_data_for_test,
    get_model,
    get_model_configs,
    get_prompt_variants,
    get_questions,
    read_ai_eval_spreadsheet,
    run_survey,
    run_survey_n_round,
    get_survey_hash
)
from lib.ai_eval_spreadsheet.schemas import EvalResultsDf, SessionResultsDf

from random import shuffle, sample
from itertools import product

# set up logger
logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)
# -

# # 1. read ai eval spreadsheet

sheet = read_ai_eval_spreadsheet()

# # 2. build question dataset

# +
# create a list of Question Objects.
questions = get_questions(sheet)

questions
# -



# # 3. construct search space and gather results

model_configs = get_model_configs(sheet)
prompt_variants = get_prompt_variants(sheet)

model_configs

prompt_variants

# +
# define a llm to eval results.

eval_llm = get_model('gpt-3.5-turbo', 'OpenAI', {})  # use this to evaluation answers with openai
# eval_llm = get_model("fakellm", "Dummy", {"answer_list": ["1", "2", "3"]})
# -

# create survey, which is a tuple of (survey_id, questions)
survey_id = get_survey_hash(questions)
survey = (survey_id, questions)
survey

# +
# we can evaluate one prompt/model pair using run_survey and run_survey_n_round
# run_survey_n_round will run n times according to model config.
# run_survey only runs one time.
# use verbose=True to get formatted prompt to be sent to LLM.

# NOTE: if the prompt has `history` field but model donesn't have memory=True, and vice visa, it will result in error.
run_survey(
    survey,
    prompt_variants[1],
    model_configs[3],
    eval_llm,
    verbose=True
)


# +
# the past evaluation records
evaluated_configs = sheet.session_results.data.df[
    ["model_configuration_id", "prompt_variation_id", "survey_id"]
].drop_duplicates()

evaluated_configs
# -

# whether run all configurations.
# If set to TRUE, all model configuration/prompt variation pairs will be evaluated.
# If set to FALSE, the model configuration/prompt variation pairs which are in the evaluated_configs will be skipped.
RERUN_ALL = True

# create a new survey from the list of questions.
# survey ID is based on question_id for each question. The order of questions
# will also affect the survey ID.
shuffle(questions)
survey_id = get_survey_hash(questions)
survey = (survey_id, questions)
survey

# +
# iterate over search space
search_space = product(model_configs, prompt_variants)

session_result = []

for model_conf, prompt_var in search_space:
    model, conf = model_conf
    model_config_id = conf.model_config_id
    prompt_var_id = prompt_var.variation_id

    # check if the prompt and model conf can be used together.
    # if prompt template includes `history` key, then model should have memory=True, and vice visa
    if ("{history}" in prompt_var.question_prompt_template and not conf.memory):
        logger.warning(f"{prompt_var_id}, {model_config_id}:")
        logger.warning("prompt template has history but model memory is not enabled. Skipped")
        continue
    if ("{history}" not in prompt_var.question_prompt_template and conf.memory):
        logger.warning(f"{prompt_var_id}, {model_config_id}:")
        logger.warning("model memory is enabled but prompt template does not support history. Skipped")
        continue
    is_evaluated = evaluated_configs.loc[
        (evaluated_configs["model_configuration_id"] == model_config_id)
        & (evaluated_configs["prompt_variation_id"] == prompt_var_id)
        & (evaluated_configs["survey_id"] == survey_id)
    ]
    if is_evaluated.empty:
        session_result.append(
            (
                (survey_id, model_config_id, prompt_var_id),
                run_survey_n_round(
                    survey=survey,
                    prompt_var=prompt_var,
                    model_conf=model_conf,
                    eval_llm=eval_llm
                ),
            )
        )
    elif RERUN_ALL is True:
        session_result.append(
            (
                (survey_id, model_config_id, prompt_var_id),
                run_survey_n_round(
                    survey=survey,
                    prompt_var=prompt_var,
                    model_conf=model_conf,
                    eval_llm=eval_llm
                ),
            )
        )
    else:
        logger.debug(
            f"({model_config_id}, {prompt_var_id}, {survey_id}) has been evaluated."
        )


# +
# create a dataframe and upload the session results:

session_recs = []
for _, lst in session_result:
    session_recs.extend(lst)
# -

session_df = pd.DataFrame.from_records(session_recs)
session_df = SessionResultsDf.validate(session_df)
session_df

if RERUN_ALL:
    sheet.session_results.replace_data(session_df)
else:
    sheet.session_results.append_data(session_df)




# # 4. construct the result dataframe

# +
# FIXME: add more metrics.


# report_df_records = []
# current_time = datetime.isoformat(datetime.utcnow())
# for k, lst in session_result:
#     logger.debug(k)
#     question_id, model_config_id, prompt_var_id = k
#     grade_counts = Counter([v["grade"] for v in lst])
#     # check result, if we found that top 2 of most common
#     # grade have the same number, then the result is undefined.
#     top2 = grade_counts.most_common(2)
#     if top2[0][1] == top2[1][1]:
#         logger.debug(f"can not determine the result: {top2}")
#         result = 'n/a'
#     else:
#         result = top2[0][0]
#     rec = {
#         "last_evaluation_datetime": current_time,
#         "question_id": question_id,
#         "model_configuration_id": model_config_id,
#         "prompt_variation_id": prompt_var_id,
#         "correct_count": grade_counts.get("correct", 0),
#         "wrong_count": grade_counts.get("wrong", 0),
#         "very_wrong_count": grade_counts.get("very wrong", 0),
#         "eval_failed_count": grade_counts.get("failed", 0),
#         "result": result
#     }
#     report_df_records.append(rec)


# report_df = pd.DataFrame.from_records(report_df_records)
# report_df = EvalResultsDf.validate(report_df)
# report_df

# +
# upload to google spreadsheet

if RERUN_ALL:
    sheet.evaluation_results.replace_data(report_df)
else:
    # There is a bug in below append_data function
    sheet.evaluation_results.append_data(report_df)

# +
# done!
