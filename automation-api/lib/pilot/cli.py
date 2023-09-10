import argparse
import logging
import os
import pathlib
import sys
from functools import partial
from itertools import product
from multiprocessing import Pool
from typing import Union

import pandas as pd

from lib.ai_eval_spreadsheet.schemas import SessionResultsDf
from lib.app_singleton import AppSingleton
from lib.pilot.helpers import (
    get_model,
    get_model_configs,
    get_prompt_variants,
    get_questions,
    get_survey_hash,
    read_ai_eval_spreadsheet,
    run_survey_n_round,
)


def run_evaluation(
    model_config_and_prompt, survey, eval_llm, evaluated_configs, append, out_dir
) -> Union[None, SessionResultsDf]:
    model_conf, prompt_var = model_config_and_prompt
    model, conf = model_conf
    model_config_id = conf.model_config_id
    prompt_var_id = prompt_var.variation_id
    survey_id = survey[0]

    out_file_path = os.path.join(
        out_dir, "_".join([model_config_id, prompt_var_id, survey_id]) + ".csv"
    )

    if os.path.exists(out_file_path):
        logger.warning("sessioin file exists, return it as is")
        session_df = pd.read_csv(out_file_path)
        session_df = SessionResultsDf.validate(session_df)
        return session_df

    session_result = []

    # check if the prompt and model conf can be used together.
    # if prompt template includes `history` key, then model should have memory=True, and vice visa
    if "{history}" in prompt_var.question_prompt_template and not conf.memory:
        logger.warning(f"{prompt_var_id}, {model_config_id}:")
        logger.warning(
            "prompt template has history but model memory is not enabled. Skipped"
        )
        return None
    if "{history}" not in prompt_var.question_prompt_template and conf.memory:
        logger.warning(f"{prompt_var_id}, {model_config_id}:")
        logger.warning(
            "model memory is enabled but prompt template does not support history. Skipped"
        )
        return None
    is_evaluated = evaluated_configs.loc[
        (evaluated_configs["model_configuration_id"] == model_config_id)
        & (evaluated_configs["prompt_variation_id"] == prompt_var_id)
        & (evaluated_configs["survey_id"] == survey_id)
    ]
    if is_evaluated.empty:
        session_result.extend(
            run_survey_n_round(
                survey=survey,
                prompt_var=prompt_var,
                model_conf=model_conf,
                eval_llm=eval_llm,
            )
        )
    elif append is False:
        session_result.extend(
            run_survey_n_round(
                survey=survey,
                prompt_var=prompt_var,
                model_conf=model_conf,
                eval_llm=eval_llm,
            )
        )
    else:
        logger.warning(
            f"({model_config_id}, {prompt_var_id}, {survey_id}) has been evaluated."
        )
    session_df = pd.DataFrame.from_records(session_result)
    session_df = SessionResultsDf.validate(session_df)
    # write result to tmp file.
    session_df.to_csv(out_file_path, index=False)
    logger.info(f"session saved to {out_file_path}")

    return session_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-j", "--jobs", default=1, type=int, help="Use how many cpu processes to run"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="Run in debug mode"
    )
    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        default=False,
        help="Append the session result to GSpreadsheet",
    )
    parser.add_argument(
        "-t",
        "--tmp_dir",
        type=pathlib.Path,
        default=pathlib.Path("./output"),
        help="Dir to store the cached session results (default to ./output)",
    )

    args = parser.parse_args()

    logger = AppSingleton().get_logger()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # create tmp file path.
    os.makedirs(args.tmp_dir, exist_ok=True)

    # # 1. read ai eval spreadsheet
    sheet = read_ai_eval_spreadsheet()
    # # 2. read data from sheets
    questions = get_questions(sheet)
    model_configs = get_model_configs(sheet)
    prompt_variants = get_prompt_variants(sheet)
    # the past evaluation records
    evaluated_configs = sheet.session_results.data.df[
        ["model_configuration_id", "prompt_variation_id", "survey_id"]
    ].drop_duplicates()

    survey_id = get_survey_hash(questions)
    survey = (survey_id, questions)

    # FIXME: add support to set eval llm and parameters.
    eval_llm = get_model(
        "gpt-3.5-turbo", "OpenAI", {"temperature": 0, "request_timeout": 120}
    )

    search_space = list(product(model_configs, prompt_variants))

    threaded_func = partial(
        run_evaluation,
        survey=survey,
        eval_llm=eval_llm,
        evaluated_configs=evaluated_configs,
        append=args.append,
        out_dir=args.tmp_dir,
    )

    if args.jobs == 1:
        session_dfs = [threaded_func(v) for v in search_space]
    else:
        with Pool(args.jobs) as p:
            session_dfs = p.map(threaded_func, search_space)

    try:
        session_df = pd.concat(session_dfs)
    except ValueError as e:
        logger.warning(str(e))
        sys.exit(127)

    print(session_df.head())

    # if args.append is False:
    #     sheet.session_results.replace_data(session_df)
    # else:
    #     sheet.session_results.append_data(session_df)

    logger.info("done!")
