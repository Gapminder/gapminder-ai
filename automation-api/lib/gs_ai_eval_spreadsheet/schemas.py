from typing import Optional

import pandera as pa
from pandera.engines.pandas_engine import PydanticModel
from pydantic import BaseModel, Field

# Schemas like these protects us from unexpected changes to the spreadsheets structure
# A combination of Pydantic and Pandera is used to be able to specify expected
# schemas for the spreadsheet data
# See https://pandera.readthedocs.io/en/stable/pydantic_integration.html
# for more info
# Note that most types are str since spreadsheet columns can be formulas
from lib.gsheets.utils import get_pydantic_model_field_titles


class Question(BaseModel):
    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation"
    )
    question_id: Optional[int] = Field(None, title="Question ID")
    survey_id: Optional[int] = Field(None, title="Survey ID")
    survey_name: Optional[str] = Field(None, title="Survey Name")
    survey_question_id: Optional[int] = Field(None, title="Survey Question ID")
    question_number: Optional[int] = Field(None, title="Question number")
    question_as_in_g_survey: Optional[str] = Field(
        None, title="Question (as in G Survey)"
    )
    expect_igno: Optional[str] = Field(None, title="Expect igno")
    published_version_of_question: Optional[str] = Field(
        None, title="Published version of question"
    )
    results_summary: Optional[str] = Field(None, title="Results summary")
    correct_answer: Optional[str] = Field(None, title="Correct Answer")
    very_wrong_answer: Optional[str] = Field(
        None,
        title="Very Wrong Answer - filled out only if it can't be derived numerically",
    )
    contentful_id: Optional[str] = Field(None, title="Contentful ID")
    upgrader_link: Optional[str] = Field(None, title="upgrader_link")


class QuestionsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(Question)
        coerce = True


class QuestionOption(BaseModel):
    question_id: Optional[int] = Field(None, title="Question ID")
    survey_id: Optional[int] = Field(None, title="Survey ID")
    survey_name: Optional[str] = Field(None, title="Survey Name")
    survey_question_id: Optional[int] = Field(None, title="Survey Question ID")
    question_number: Optional[int] = Field(None, title="Question number")
    question_text: Optional[str] = Field(None, title="Question text")
    letter: Optional[str] = Field(None, title="Letter")
    question_option: Optional[str] = Field(None, title="Question option")
    correctness_of_answer_option: Optional[str] = Field(
        None, title="Correctness of answer option"
    )
    human_answer_percentage: Optional[float] = Field(
        None, title="Human answer percentage"
    )


class QuestionOptionsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(QuestionOption)
        coerce = True


class PromptVariation(BaseModel):
    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation"
    )
    variation_id: Optional[int] = Field(None, title="Variation ID")
    question_prompt_template: Optional[str] = Field(
        None, title="Question prompt template"
    )
    question_prompt_template_example: Optional[str] = Field(
        None, title="Question prompt template example"
    )
    follow_up_answer_correctness_evaluation_prompt_template: Optional[str] = Field(
        None, title="Follow-up answer correctness evaluation prompt template"
    )


class PromptVariationsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(PromptVariation)
        coerce = True


class GenAiModel(BaseModel):
    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation"
    )
    model_id: Optional[int] = Field(None, title="Model ID")
    vendor: Optional[str] = Field(None, title="Vendor")
    model_name: Optional[str] = Field(None, title="Model name")


class GenAiModelsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(GenAiModel)
        coerce = True


class GsAiEvalData(BaseModel):
    questions: Optional[QuestionsDf] = Field(None, title="Questions")
    question_options: Optional[QuestionOptionsDf] = Field(
        None, title="Question options"
    )
    prompt_variations: Optional[PromptVariationsDf] = Field(
        None, title="Prompt variations"
    )
    models: Optional[GenAiModelsDf] = Field(None, title="Models")


sheet_names = get_pydantic_model_field_titles(GsAiEvalData)
