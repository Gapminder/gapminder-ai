import json
from itertools import product
from typing import Any, Dict, List, Tuple

import pandas as pd
from langchain.chains import LLMChain
from langchain.llms.base import LLM
from langchain.prompts import PromptTemplate
from pandera.errors import SchemaError

from lib.ai_eval_spreadsheet.schemas import (
    GenAiModel,
    GenAiModelConfig,
    PromptVariation,
    Question,
    QuestionOption,
)
from lib.ai_eval_spreadsheet.wrapper import (
    AiEvalData,
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
)
from lib.app_singleton import AppSingleton
from lib.authorized_clients import get_service_account_authorized_clients
from lib.config import read_config
from lib.llms.utils import get_dummy_model, get_openai_model

logger = AppSingleton().get_logger()


# defining type alias to make function types more easier to write
QuestionAndOptions = Tuple[Question, List[QuestionOption]]
ModelAndConfig = Tuple[GenAiModel, GenAiModelConfig]


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


def class_objects_from_df(df: pd.DataFrame, cls: type) -> list:
    # FIXME: how to write correct type annotation for this?
    return [cls(**rec) for rec in df.to_dict(orient="records")]


def get_questions(sheet: AiEvalData) -> List[QuestionAndOptions]:
    questions = filter_included_rows(sheet.questions.data.df)
    options = sheet.question_options.data.df
    qs = class_objects_from_df(questions, Question)

    res = []
    for q in qs:
        qid = q.question_id
        qopts = [
            QuestionOption(**rec)
            for rec in options.loc[options["question_id"] == qid].to_dict(
                orient="records"
            )
        ]
        res.append((q, qopts))

    return res


def get_model(model_id, vendor, model_conf):
    if vendor == "OpenAI":
        return get_openai_model(model_id, **model_conf)
    elif vendor == "Dummy":
        return get_dummy_model(model_id, **model_conf)
    else:
        raise NotImplementedError(f"{model_id} from {vendor} is not supported yet.")


def option_text(opt: QuestionOption, letter_and_text: bool = True) -> str:
    if letter_and_text:
        return f"{opt.letter}. {opt.question_option}"
    else:
        return opt.letter


def simple_evaluation(question: QuestionAndOptions, answer: str) -> str:
    correctness_map = {1: "correct", 2: "wrong", 3: "very wrong"}
    # some times the model will return 'A.' instead of 'A'
    if len(answer) == 2 and answer[1] == ".":
        answer = answer[0]

    for opt in question[1]:
        if answer == opt.letter or answer == option_text(opt, letter_and_text=True):
            return correctness_map[opt.correctness_of_answer_option]
    return "failed"


def create_question_data_for_test(question: QuestionAndOptions) -> Dict[str, str]:
    q, options = question
    question_dict = {"question": q.published_version_of_question}
    question_dict["options"] = "\n".join(
        [option_text(opt, letter_and_text=True) for opt in options]
    )
    return question_dict


def create_question_dataset_for_test(
    question_list: List[QuestionAndOptions],
) -> List[Dict[str, str]]:
    return [create_question_data_for_test(q) for q in question_list]


def create_question_data_for_eval(question: QuestionAndOptions) -> Dict[str, str]:
    q, options = question
    question_dict = {}
    question_text_list = [q.published_version_of_question]
    for opt in options:
        opt_text = option_text(opt, letter_and_text=True)
        question_text_list.append(opt_text)
        if opt.correctness_of_answer_option == 1:
            question_dict["correct_answer"] = opt_text
        elif opt.correctness_of_answer_option == 2:
            question_dict["wrong_answer"] = opt_text
        else:
            question_dict["very_wrong_answer"] = opt_text
    question_dict["question"] = "\n".join(question_text_list)
    return question_dict


def create_question_dataset_for_eval(
    question_list: List[QuestionAndOptions],
) -> List[Dict[str, str]]:
    return [create_question_data_for_eval(q) for q in question_list]


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
    prompt_variations = filter_included_rows(sheet.prompt_variations.data.df)
    res = class_objects_from_df(prompt_variations, PromptVariation)
    return res


def get_model_configs(sheet: AiEvalData) -> List[ModelAndConfig]:
    models_df = sheet.gen_ai_models.data.df
    model_configs_df = filter_included_rows(sheet.gen_ai_model_configs.data.df)

    model_configs = class_objects_from_df(model_configs_df, GenAiModelConfig)
    result = []
    for mc in model_configs:
        model_df = models_df.loc[models_df["model_id"] == mc.model_id]
        model = class_objects_from_df(model_df, GenAiModel)[0]
        result.append((model, mc))
    return result


def load_model_parameters(s: str) -> Dict[str, Any]:
    if s == "nan":
        # NOTE: nan (float) value has converted to 'nan' (string)
        # by the reader. That's why I am checking with 'nan' here.
        return {}
    return json.loads(s)


def run_evaluation(
    question: QuestionAndOptions,
    prompt_var: PromptVariation,
    model_conf: ModelAndConfig,
    eval_llm: LLM,
) -> List[Dict[str, Any]]:
    # get some variables
    model, conf = model_conf
    model_id = model.model_id
    model_parameters = load_model_parameters(conf.model_parameters)
    prompt_id = prompt_var.variation_id
    model_config_id = conf.model_config_id
    vendor = model.vendor
    question_id = question[0].question_id
    logger.debug(f"running model: {model_id}")
    logger.debug(f"parameters: {model_parameters}")
    logger.debug(f"question ID: {question_id}")
    llm = get_model(model_id, vendor, model_parameters)
    # create question data
    question_data = create_question_data_for_test(question)
    eval_data = create_question_data_for_eval(question)
    # create llm related vavriables
    prompt_tmpl = PromptTemplate.from_template(prompt_var.question_prompt_template)
    chain = LLMChain(llm=llm, prompt=prompt_tmpl)

    followup = prompt_var.follow_up_answer_correctness_evaluation_prompt_template
    # gather results
    result = []
    for t in range(conf.repeat_times):
        res = {
            "model_config_id": model_config_id,
            "prompt_id": prompt_id,
            "question_id": question_id,
            "round": t,
        }
        logger.debug(f"prompt {prompt_id}, round {t}")
        # ask llm to answer questions
        output = chain.run(question_data)
        res["output"] = output

        # preform a correctness checking
        # followup = prompt_var.followup_prompt_template
        if followup == "nan":  # simple string matching
            # NOTE: nan (float) value has converted to 'nan' (string)
            # by the reader. That's why I am checking with 'nan' here.
            logger.debug("using string comparing method to evaluate")
            res["grade"] = simple_evaluation(question, output)
        else:  # use LLM to eval
            logger.debug("using LLM method to evaluate")
            followup_tmpl = PromptTemplate.from_template(followup)
            eval_chain = LLMChain(llm=eval_llm, prompt=followup_tmpl)
            # combine the output and eval dataset
            eval_data["text"] = output
            grade_output = eval_chain.run(eval_data)
            grade = check_llm_eval_output(grade_output)
            res["grade"] = grade
        result.append(res)
    return result


def get_search_space(
    questions: List[QuestionAndOptions],
    model_configs: List[ModelAndConfig],
    prompt_variants: List[PromptVariation],
):
    return product(questions, model_configs, prompt_variants)
