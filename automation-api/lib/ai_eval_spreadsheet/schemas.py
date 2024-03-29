# Schemas like these protects us from unexpected changes to the spreadsheets structure
# A combination of Pydantic and Pandera is used to be able to specify expected
# schemas for the spreadsheet data
# See https://pandera.readthedocs.io/en/stable/pydantic_integration.html
# for more info
# Note that most types are str since spreadsheet columns can be formulas

from typing import Optional

import pandas as pd
import pandera as pa
from pandera.engines.pandas_engine import PydanticModel
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Question(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation", validate_default=True
    )
    question_id: Optional[str] = Field(None, title="Question ID")
    language: Optional[str] = Field(None, title="Language")
    published_version_of_question: Optional[str] = Field(
        None, title="Published version of question"
    )

    @field_validator("include_in_next_evaluation", mode="before")
    @classmethod
    def default_if_nan(cls, v):  # noqa: N805
        return False if pd.isna(v) else v


class QuestionsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(Question)
        coerce = True


class QuestionOption(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    question_option_id: Optional[str] = Field(None, title="Question Option ID")
    question_id: Optional[str] = Field(None, title="Question ID")
    language: Optional[str] = Field(None, title="Language")
    letter: Optional[str] = Field(None, title="Letter")
    question_option: Optional[str] = Field(None, title="Question option")
    correctness_of_answer_option: Optional[int] = Field(
        None, title="Correctness of answer option"
    )


class QuestionOptionsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(QuestionOption)
        coerce = True


class PromptVariation(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation"
    )
    variation_id: Optional[str] = Field(None, title="Variation ID")
    language: Optional[str] = Field(None, title="Language")
    question_template: Optional[str] = Field(None, title="Question template")
    question_prefix: Optional[str] = Field(None, title="Question prefix")
    ai_prefix: Optional[str] = Field(None, title="AI prefix")
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
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    model_id: Optional[str] = Field(None, title="Model ID")
    vendor: Optional[str] = Field(None, title="Vendor")
    model_name: Optional[str] = Field(None, title="Model name")


class GenAiModelsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(GenAiModel)
        coerce = True


class GenAiModelConfig(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    include_in_next_evaluation: Optional[bool] = Field(
        None, title="Include in next evaluation"
    )
    model_config_id: Optional[str] = Field(None, title="Model configuration ID")
    model_id: Optional[str] = Field(None, title="Model ID")
    model_parameters: Optional[str] = Field(None, title="Model Parameters")
    repeat_times: Optional[int] = Field(None, title="Repeat Times")
    memory: Optional[bool] = Field(None, title="Memory")
    memory_size: Optional[int] = Field(None, title="Memory Size")


class GenAiModelConfigsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(GenAiModelConfig)
        coerce = True


class Metric(BaseModel):
    name: Optional[str] = Field(None, title="Name")
    description: Optional[str] = Field(None, title="Description")
    prompt: Optional[str] = Field(None, title="Prompt")
    choices: Optional[str] = Field(None, title="Choices")
    choice_scores: Optional[str] = Field(None, title="Choice Scores")


class MetricsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(Metric)
        coerce = True


class EvalResult(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    question_id: Optional[str] = Field(None, title="Question ID")
    language: Optional[str] = Field(None, title="Language")
    prompt_variation_id: Optional[str] = Field(None, title="Prompt variation ID")
    model_configuration_id: Optional[str] = Field(None, title="Model Configuration ID")
    last_evaluation_datetime: Optional[str] = Field(None, title="Last Evaluation")
    percent_correct: Optional[float] = Field(None, title="Percent Correct")
    percent_wrong: Optional[float] = Field(None, title="Percent Wrong")
    percent_very_wrong: Optional[float] = Field(None, title="Percent Very Wrong")
    percent_eval_failed: Optional[float] = Field(None, title="Percent Eval Failed")
    rounds: Optional[int] = Field(None, title="Rounds")
    result: Optional[str] = Field(None, title="Result")


class EvalResultsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(EvalResult)
        coerce = True


class SessionResult(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    session_id: Optional[str] = Field(None, title="Session ID")
    session_time: Optional[str] = Field(None, title="Session Time")
    prompt_variation_id: Optional[str] = Field(None, title="Prompt Variation ID")
    model_configuration_id: Optional[str] = Field(None, title="Model Configuration ID")
    survey_id: Optional[str] = Field(None, title="Survey ID")
    question_id: Optional[str] = Field(None, title="Question ID")
    language: Optional[str] = Field(None, title="Language")
    question_number: Optional[int] = Field(None, title="Question No.")
    output: Optional[str] = Field(None, title="Response Text")
    grade: Optional[str] = Field(None, title="Grade")


class SessionResultsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(SessionResult)
        coerce = True
