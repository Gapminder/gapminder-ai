from dataclasses import dataclass
from typing import Type

from gspread import Spreadsheet

from lib.ai_eval_spreadsheet.schemas import (
    Evaluator,
    EvaluatorsDf,
    GenAiModel,
    GenAiModelConfig,
    GenAiModelConfigsDf,
    GenAiModelsDf,
    Metric,
    MetricsDf,
    PromptVariation,
    PromptVariationsDf,
    Question,
    QuestionOption,
    QuestionOptionsDf,
    QuestionsDf,
)
from lib.gdrive.auth import AuthorizedClients
from lib.gsheets.gsheets_worksheet_editor import GsheetsWorksheetEditor


@dataclass
class AiEvalData:
    prompt_variations: GsheetsWorksheetEditor[
        Type[PromptVariationsDf], Type[PromptVariation]
    ]
    questions: GsheetsWorksheetEditor[Type[QuestionsDf], Type[Question]]
    question_options: GsheetsWorksheetEditor[
        Type[QuestionOptionsDf], Type[QuestionOption]
    ]
    gen_ai_models: GsheetsWorksheetEditor[Type[GenAiModelsDf], Type[GenAiModel]]
    gen_ai_model_configs: GsheetsWorksheetEditor[
        Type[GenAiModelConfigsDf], Type[GenAiModelConfig]
    ]
    metrics: GsheetsWorksheetEditor[Type[MetricsDf], Type[Metric]]
    evaluators: GsheetsWorksheetEditor[Type[EvaluatorsDf], Type[Evaluator]]


sheet_names = {
    "questions": "Questions",
    "question_options": "Question options",
    "prompt_variations": "Prompt variations",
    "gen_ai_models": "Models",
    "gen_ai_model_configs": "Model configurations",
    "metrics": "Metrics",
    "evaluators": "Evaluators",
}


def get_ai_eval_spreadsheet(
    authorized_clients: AuthorizedClients, ai_eval_spreadsheet_id: str
) -> Spreadsheet:
    ai_eval_spreadsheet = authorized_clients.gc.open_by_key(ai_eval_spreadsheet_id)
    return ai_eval_spreadsheet


def read_ai_eval_data(
    ai_eval_spreadsheet: Spreadsheet,
) -> AiEvalData:
    questions = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=QuestionsDf,
        row_schema=Question,
        worksheet_name=sheet_names["questions"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    question_options = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=QuestionOptionsDf,
        row_schema=QuestionOption,
        worksheet_name=sheet_names["question_options"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    prompt_variations = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=PromptVariationsDf,
        row_schema=PromptVariation,
        worksheet_name=sheet_names["prompt_variations"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    gen_ai_models = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=GenAiModelsDf,
        row_schema=GenAiModel,
        worksheet_name=sheet_names["gen_ai_models"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    gen_ai_model_configs = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=GenAiModelConfigsDf,
        row_schema=GenAiModelConfig,
        worksheet_name=sheet_names["gen_ai_model_configs"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    metrics = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=MetricsDf,
        row_schema=Metric,
        worksheet_name=sheet_names["metrics"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    evaluators = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=EvaluatorsDf,
        row_schema=Evaluator,
        worksheet_name=sheet_names["evaluators"],
        header_row_number=0,
        evaluate_formulas=False,
    )

    return AiEvalData(
        questions=questions,
        question_options=question_options,
        prompt_variations=prompt_variations,
        gen_ai_models=gen_ai_models,
        gen_ai_model_configs=gen_ai_model_configs,
        metrics=metrics,
        evaluators=evaluators,
    )
