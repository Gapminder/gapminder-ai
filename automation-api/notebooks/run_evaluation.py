# +
import logging
from datetime import datetime
from functools import partial

import pandas as pd

from lib.app_singleton import AppSingleton
from lib.pilot.helpers import (
    count_grades,
    create_question_dataset_for_eval,
    create_question_dataset_for_test,
    get_model,
    get_model_configs,
    get_prompt_variants,
    get_questions,
    get_search_space,
    read_ai_eval_spreadsheet,
    run_evaluation_,
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
questions_list = get_questions(sheet)

# create test dataset and eval dataset
question_dataset = create_question_dataset_for_test(questions_list)
eval_dataset = create_question_dataset_for_eval(questions_list)

# The question_dataset only have question and options, and will be used to test the LLM.
# and the eval_dataset have question and answer grades, and will be used to evaluatet the result returned by LLM.
# -

questions_list

question_dataset

eval_dataset

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
run_evaluation_(
    questions_list,
    question_dataset,
    eval_dataset,
    prompt_variants[0],
    model_configs[0],
    eval_llm,
)

# +
# define a convenience function

run_evaluation_with_dataset = partial(
    run_evaluation_,
    questions_list=questions_list,
    question_dataset=question_dataset,
    eval_dataset=eval_dataset,
    eval_llm=eval_llm,
)

# +
# the past evaluation records
evaluated_configs = sheet.evaluation_results.data.df[
    ["model_configuration_id", "prompt_variation_id"]
].drop_duplicates()

evaluated_configs
# -

# whether run all configurations.
# If set to TRUE, all model configuration/prompt variation pairs will be evaluated.
# If set to FALSE, the model configuration/prompt variation pairs which are in the evaluated_configs will be skipped.
RERUN_ALL = True

# +
# iterate over search space

search_space = get_search_space(model_configs, prompt_variants)

eval_result = []

for model_conf, prompt_var in search_space:
    model_config_id = model_conf.model_config_id
    prompt_var_id = prompt_var.variation_id
    is_evaluated = evaluated_configs.loc[
        (evaluated_configs["model_configuration_id"] == model_config_id)
        & (evaluated_configs["prompt_variation_id"] == prompt_var_id)
    ]
    if is_evaluated.empty:
        eval_result.append(
            (
                (model_config_id, prompt_var_id),
                run_evaluation_with_dataset(
                    prompt_var=prompt_var, model_conf=model_conf
                ),
            )
        )
    elif RERUN_ALL is True:
        eval_result.append(
            (
                (model_config_id, prompt_var_id),
                run_evaluation_with_dataset(
                    prompt_var=prompt_var, model_conf=model_conf
                ),
            )
        )
    else:
        logger.debug(
            f"({model_config_id}, {prompt_var_id}) has been evaluated."
        )

eval_result
# -

# # 4. construct the result dataframe

# +
report_df_records = []
current_time = datetime.isoformat(datetime.utcnow())
for k, lst in eval_result:
    print(k)
    vs = [v["grades"] for v in lst]
    # print(vs)
    grade_counts = count_grades(vs)
    q_and_g = zip(questions_list, grade_counts)
    for q, g in q_and_g:
        rec = {
            "last_evaluation_datetime": current_time,
            "question_id": q.question_id,
            "model_configuration_id": k[0],
            "prompt_variation_id": k[1],
            "correct_count": g.get("correct", 0),
            "wrong_count": g.get("wrong", 0),
            "very_wrong_count": g.get("very wrong", 0),
            "eval_failed_count": g.get("failed", 0),
            "result": g.most_common(1)[0][0],
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
# -
