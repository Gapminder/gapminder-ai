from dataclasses import dataclass
from typing import Optional

from gspread import Spreadsheet

from lib.ai_eval_spreadsheet.schemas import (
    GenAiModel,
    GenAiModelsDf,
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
    questions: Optional[GsheetsWorksheetEditor[QuestionsDf, Question]] = None
    question_options: Optional[
        GsheetsWorksheetEditor[QuestionOptionsDf, QuestionOption]
    ] = None
    prompt_variations: Optional[
        GsheetsWorksheetEditor[PromptVariationsDf, PromptVariation]
    ] = None
    gen_ai_models: Optional[GsheetsWorksheetEditor[GenAiModelsDf, GenAiModel]] = None


sheet_names = {
    "questions": "Questions",
    "question_options": "Question options",
    "prompt_variations": "Prompt variations",
    "gen_ai_models": "Models",
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
        # attributes_to_columns_map=get_pydantic_model_field_titles(Question),
        evaluate_formulas=True,
    )

    question_options = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=QuestionOptionsDf,
        row_schema=QuestionOption,
        worksheet_name=sheet_names["question_options"],
        header_row_number=0,
        # attributes_to_columns_map=get_pydantic_model_field_titles(Question),
        evaluate_formulas=True,
    )

    prompt_variations = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=PromptVariationsDf,
        row_schema=PromptVariation,
        worksheet_name=sheet_names["prompt_variations"],
        header_row_number=0,
        evaluate_formulas=True,
    )

    gen_ai_models = GsheetsWorksheetEditor(
        sh=ai_eval_spreadsheet,
        df_schema=GenAiModelsDf,
        row_schema=GenAiModel,
        worksheet_name=sheet_names["gen_ai_models"],
        header_row_number=0,
        evaluate_formulas=True,
    )

    return AiEvalData(
        questions=questions,
        question_options=question_options,
        prompt_variations=prompt_variations,
        gen_ai_models=gen_ai_models,
    )
