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
    get_search_space,
    read_ai_eval_spreadsheet,
    run_evaluation,
)
from lib.ai_eval_spreadsheet.schemas import EvalResultsDf

# set up logger
logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)
# -

# # 1. read ai eval spreadsheet

sheet = read_ai_eval_spreadsheet()

# # 2. build question datasets

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

# eval_llm = get_model('gpt-3.5-turbo', 'OpenAI', {})  # use this to evaluation answers with openai
eval_llm = get_model("fakellm", "Dummy", {"answer_list": ["1", "2", "3"]})
# -

# we can evaluate one prompt/model pair using this function
run_evaluation(
    questions[0],
    prompt_variants[2],
    model_configs[0],
    eval_llm,
)


# +
# the past evaluation records
evaluated_configs = sheet.evaluation_results.data.df[
    ["model_configuration_id", "prompt_variation_id", "question_id"]
].drop_duplicates()

evaluated_configs
# -

# whether run all configurations.
# If set to TRUE, all model configuration/prompt variation pairs will be evaluated.
# If set to FALSE, the model configuration/prompt variation pairs which are in the evaluated_configs will be skipped.
RERUN_ALL = True

# +
# iterate over search space

search_space = get_search_space(questions,
                                model_configs,
                                prompt_variants)

eval_result = []

for question_and_opts, model_conf, prompt_var in search_space:
    question, options = question_and_opts
    model, conf = model_conf
    model_config_id = conf.model_config_id
    prompt_var_id = prompt_var.variation_id
    question_id = question.question_id
    is_evaluated = evaluated_configs.loc[
        (evaluated_configs["model_configuration_id"] == model_config_id)
        & (evaluated_configs["prompt_variation_id"] == prompt_var_id)
        & (evaluated_configs["question_id"] == question_id)
    ]
    if is_evaluated.empty:
        eval_result.append(
            (
                (question_id, model_config_id, prompt_var_id),
                run_evaluation(
                    question=question_and_opts,
                    prompt_var=prompt_var,
                    model_conf=model_conf,
                    eval_llm=eval_llm
                ),
            )
        )
    elif RERUN_ALL is True:
        eval_result.append(
            (
                (question_id, model_config_id, prompt_var_id),
                run_evaluation(
                    question=question_and_opts,
                    prompt_var=prompt_var,
                    model_conf=model_conf,
                    eval_llm=eval_llm
                ),
            )
        )
    else:
        logger.debug(
            f"({model_config_id}, {prompt_var_id}, {question_id}) has been evaluated."
        )

eval_result
# -

# # 4. construct the result dataframe

# +
report_df_records = []
current_time = datetime.isoformat(datetime.utcnow())
for k, lst in eval_result:
    logger.debug(k)
    question_id, model_config_id, prompt_var_id = k
    grade_counts = Counter([v["grade"] for v in lst])
    # check result, if we found that top 2 of most common
    # grade have the same number, then the result is undefined.
    top2 = grade_counts.most_common(2)
    if top2[0][1] == top2[1][1]:
        logger.debug(f"can not determine the result: {top2}")
        result = 'n/a'
    else:
        result = top2[0][0]
    rec = {
        "last_evaluation_datetime": current_time,
        "question_id": question_id,
        "model_configuration_id": model_config_id,
        "prompt_variation_id": prompt_var_id,
        "correct_count": grade_counts.get("correct", 0),
        "wrong_count": grade_counts.get("wrong", 0),
        "very_wrong_count": grade_counts.get("very wrong", 0),
        "eval_failed_count": grade_counts.get("failed", 0),
        "result": result
    }
    report_df_records.append(rec)


report_df = pd.DataFrame.from_records(report_df_records)
report_df = EvalResultsDf.validate(report_df)
report_df

# +
# upload to google spreadsheet

if RERUN_ALL:
    sheet.evaluation_results.replace_data(report_df)
else:
    # There is a bug in below append_data function
    sheet.evaluation_results.append_data(report_df)

# +
# done!
