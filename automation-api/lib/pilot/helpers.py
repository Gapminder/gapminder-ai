from collections import Counter
from itertools import product
from typing import Any, Dict, Iterable, List

import pandas as pd
from langchain.chains import LLMChain
from langchain.llms.base import LLM
from langchain.prompts import PromptTemplate
from pandera.errors import SchemaError

from lib.ai_eval_spreadsheet.wrapper import (
    AiEvalData,
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
)
from lib.app_singleton import AppSingleton
from lib.authorized_clients import get_service_account_authorized_clients
from lib.config import read_config
from lib.llms.utils import get_dummy_model, get_openai_model

from .datatypes import ModelConfig, PromptVariation, Question, QuestionOption

logger = AppSingleton().get_logger()


def read_ai_eval_spreadsheet() -> AiEvalData:
    config = read_config()
    authorized_clients = get_service_account_authorized_clients()

    ai_eval_spreadsheet_id = config["AI_EVAL_DEV_SPREADSHEET_ID"]
    ai_eval_spreadsheet = get_ai_eval_spreadsheet(
        authorized_clients, ai_eval_spreadsheet_id
    )
    try:
        return read_ai_eval_data(ai_eval_spreadsheet)
    except SchemaError as err:
        logger.error("DataFrame validation failed. Errors:", err.check)
        logger.error("Schema:")
        logger.error(err.schema)
        logger.error("Failure cases:")
        logger.error(err.failure_cases)  # dataframe of schema errors
        logger.error("Original data:")
        logger.error(err.data)  # invalid dataframe
        return None


def filter_included_rows(df: pd.DataFrame) -> pd.DataFrame:
    """filter rows that are marked TRUE in `include_in_next_evaluation` column.

    the df will return as is if `include_in_next_evaluation` column not found.
    """
    col_to_filter = "include_in_next_evaluation"
    if col_to_filter not in df.columns:
        logger.warning("include_in_next_evaluation not found")
        return df
    return df[df[col_to_filter]]


def prepare_questions_data(sheet: AiEvalData) -> pd.DataFrame:
    question_df = sheet.questions.data.df.copy()
    options_df = sheet.question_options.data.df.copy()

    enabled_questions_df = filter_included_rows(question_df)
    enabled_questions_df = enabled_questions_df[
        ["question_id", "published_version_of_question"]
    ].set_index("question_id")

    options_df = options_df[
        ["question_id", "letter", "question_option", "correctness_of_answer_option"]
    ].set_index("question_id")

    return enabled_questions_df.join(options_df, on="question_id", how="inner")


def get_questions(sheet: AiEvalData) -> List[Question]:
    qdf = prepare_questions_data(sheet)
    questions_list = []
    gs = qdf.groupby("question_id")
    for g, df in gs:
        options = list()
        qt = df["published_version_of_question"].iloc[0]
        correct_option = None
        i = 0
        for _, row in df.sort_values(by="letter").iterrows():
            letter = row["letter"]
            option_text = row["question_option"]
            correctness = row["correctness_of_answer_option"]
            options.append(QuestionOption(letter, option_text, correctness))
            if correctness == 1:
                correct_option = i
            i = i + 1
        questions_list.append(Question(g, qt, options, correct_option))
    return questions_list


def get_model(model_id, vendor, model_conf):
    if vendor == "OpenAI":
        return get_openai_model(model_id, **model_conf)
    elif vendor == "Dummy":
        return get_dummy_model(model_id, **model_conf)
    else:
        raise NotImplementedError(f"{model_id} from {vendor} is not supported yet.")


def simple_evaluation(question: Question, answer: str) -> str:
    """a simple method to grade the answer"""
    correctness_map = {1: "correct", 2: "wrong", 3: "very wrong"}
    # some times the model will return 'A.' instead of 'A'
    if len(answer) == 2 and answer[1] == ".":
        answer = answer[0]
    for opt in question.options:
        if answer == opt.letter or answer == opt.letter_and_text():
            return correctness_map[opt.correctness]
    return "failed"


def create_question_dataset_for_test(
    question_list: List[Question],
) -> List[Dict[str, str]]:
    res = []
    for question in question_list:
        question_dict = {"question": question.question_text}
        question_dict["options"] = "\n".join(
            [f"{x.letter}. {x.option_text}" for x in question.options]
        )
        res.append(question_dict)
    return res


def create_question_dataset_for_eval(
    question_list: List[Question],
) -> List[Dict[str, str]]:
    res = []
    for question in question_list:
        question_dict = {}
        question_text_list = [question.question_text]
        for opt in question.options:
            opt_text = opt.letter_and_text()
            question_text_list.append(opt_text)
            if opt.correctness == 1:
                question_dict["correct_answer"] = opt_text
            elif opt.correctness == 2:
                question_dict["wrong_answer"] = opt_text
            else:
                question_dict["very_wrong_answer"] = opt_text
        question_dict["question"] = "\n".join(question_text_list)
        res.append(question_dict)
    return res


def check_llm_eval_output(eval_output: str) -> str:
    eval_output = eval_output.strip().replace(".", "").lower()
    if eval_output == "1":
        return "correct"
    elif eval_output == "2":
        return "wrong"
    elif eval_output == "3":
        return "very wrong"
    else:
        return "failed"


def get_prompt_variants(sheet: AiEvalData) -> List[PromptVariation]:
    df = filter_included_rows(sheet.prompt_variations.data.df)
    result = []
    for _, row in df.iterrows():
        variation_id = row["variation_id"]
        question_prompt_template = row["question_prompt_template"]
        followup_prompt_template = row[
            "follow_up_answer_correctness_evaluation_prompt_template"
        ]
        result.append(
            PromptVariation(
                variation_id=variation_id,
                question_prompt_template=question_prompt_template,
                followup_prompt_template=followup_prompt_template,
            )
        )
    return result


def get_model_configs(sheet: AiEvalData) -> List[ModelConfig]:
    model_df = sheet.gen_ai_models.data.df
    model_config_df = filter_included_rows(sheet.gen_ai_model_configs.data.df)

    model_df = model_df.set_index("model_id")
    model_config_df = model_config_df.set_index("model_id")

    df = model_config_df.join(model_df, on="model_id", how="inner").reset_index()
    result = []
    for _, row in df.iterrows():
        result.append(
            ModelConfig(
                vendor=row["vendor"],
                model_config_id=row["model_config_id"],
                model_id=row["model_id"],
                repeat_times=row["repeat_times"],
                model_parameters=row["model_parameters"],
            )
        )
    return result


def run_evaluation_(
    questions_list: List[Question],
    question_dataset: List[Dict[str, str]],
    eval_dataset: List[Dict[str, str]],
    prompt_var: PromptVariation,
    model_conf: ModelConfig,
    eval_llm: LLM,
) -> List[Dict[str, Any]]:
    # get some variables
    model_id = model_conf.model_id
    model_parameters = model_conf.model_parameters
    prompt_id = prompt_var.variation_id
    model_config_id = model_conf.model_config_id
    vendor = model_conf.vendor
    logger.debug(f"running model: {model_id}")
    logger.debug(f"parameters: {model_parameters}")
    llm = get_model(model_id, vendor, model_parameters)
    result = []
    for t in range(model_conf.repeat_times):
        res = {"model_config_id": model_config_id, "prompt_id": prompt_id, "round": t}
        logger.debug(f"prompt {prompt_id}, round {t}")
        # ask llm to answer questions
        prompt_tmpl = PromptTemplate.from_template(prompt_var.question_prompt_template)
        chain = LLMChain(llm=llm, prompt=prompt_tmpl)
        output = chain.apply(question_dataset)
        res["outputs"] = output

        # preform a correctness checking
        followup = prompt_var.followup_prompt_template
        if followup == "":  # simple string matching
            logger.debug("using string comparing method to evaluate")
            qa_pairs = zip(questions_list, output)
            grades = [simple_evaluation(q, a["text"]) for q, a in qa_pairs]
            res["grades"] = grades
        else:  # use LLM to eval
            logger.debug("using LLM method to evaluate")
            followup_tmpl = PromptTemplate.from_template(followup)
            eval_chain = LLMChain(llm=eval_llm, prompt=followup_tmpl)
            # combine the output and eval dataset
            eval_inputs = []
            for i, rec in enumerate(eval_dataset):
                rec_new = rec.copy()
                rec_new["text"] = output[i]["text"]
                eval_inputs.append(rec_new)
            grades_output = eval_chain.apply(eval_inputs)
            grades = [check_llm_eval_output(x["text"]) for x in grades_output]
            res["grades"] = grades
        result.append(res)
    return result


def run_evaluation(
    questions_list: List[Question],
    prompt_var: PromptVariation,
    model_conf: ModelConfig,
    eval_llm: LLM,
) -> List[Dict[str, Any]]:
    # construct datasets from question list, which will be consumed by LLMChain.
    question_dataset = create_question_dataset_for_test(questions_list)
    eval_dataset = create_question_dataset_for_eval(questions_list)
    # this will run slower than run_evaluation_(), because we generate
    # the datasets on the fly.
    return run_evaluation_(
        questions_list, question_dataset, eval_dataset, prompt_var, model_conf, eval_llm
    )


def get_search_space(
    model_configs: List[ModelConfig], prompt_variants: List[PromptVariation]
):
    return product(model_configs, prompt_variants)


def count_grades(it: List[Iterable[str]]) -> List[Counter]:
    res = []
    for x in zip(*it):
        res.append(Counter(x))
    return res
