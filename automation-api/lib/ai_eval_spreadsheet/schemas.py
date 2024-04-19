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

    include_in_next_evaluation: bool = Field(
        False, title="Include in next evaluation", validate_default=True
    )
    question_id: str = Field("", title="Question ID")
    language: str = Field("", title="Language")
    published_version_of_question: str = Field(
        "", title="Published version of question"
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

    question_option_id: str = Field("", title="Question Option ID")
    question_id: str = Field("", title="Question ID")
    language: str = Field("", title="Language")
    letter: str = Field("", title="Letter")
    question_option: str = Field("", title="Question option")
    correctness_of_answer_option: int = Field(-1, title="Correctness of answer option")


class QuestionOptionsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(QuestionOption)
        coerce = True


class PromptVariation(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    include_in_next_evaluation: bool = Field(False, title="Include in next evaluation")
    variation_id: str = Field("", title="Variation ID")
    language: str = Field("", title="Language")
    question_template: str = Field("", title="Question template")
    question_prefix: str = Field("", title="Question prefix")
    ai_prefix: str = Field("", title="AI prefix")
    question_prompt_template: str = Field("", title="Question prompt template")
    question_prompt_template_example: str = Field(
        "", title="Question prompt template example"
    )
    follow_up_answer_correctness_evaluation_prompt_template: str = Field(
        "", title="Follow-up answer correctness evaluation prompt template"
    )


class PromptVariationsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(PromptVariation)
        coerce = True


class GenAiModel(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    model_id: str = Field("", title="Model ID")
    vendor: str = Field("", title="Vendor")
    model_name: str = Field("", title="Model name")


class GenAiModelsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(GenAiModel)
        coerce = True


class GenAiModelConfig(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    include_in_next_evaluation: bool = Field(False, title="Include in next evaluation")
    model_config_id: str = Field("", title="Model configuration ID")
    model_id: str = Field("", title="Model ID")
    model_parameters: str = Field("", title="Model Parameters")
    repeat_times: int = Field(-1, title="Repeat Times")
    memory: bool = Field(False, title="Memory")
    memory_size: int = Field(-1, title="Memory Size")


class GenAiModelConfigsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(GenAiModelConfig)
        coerce = True


class Metric(BaseModel):
    name: str = Field("", title="Name")
    description: str = Field("", title="Description")
    prompt: str = Field("", title="Prompt")
    choices: str = Field("", title="Choices")
    choice_scores: str = Field("", title="Choice Scores")


class MetricsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(Metric)
        coerce = True


class EvalResult(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    question_id: str = Field("", title="Question ID")
    language: str = Field("", title="Language")
    prompt_variation_id: str = Field("", title="Prompt variation ID")
    model_configuration_id: str = Field("", title="Model Configuration ID")
    last_evaluation_datetime: str = Field("", title="Last Evaluation")
    percent_correct: Optional[float] = Field("", title="Percent Correct")
    percent_wrong: Optional[float] = Field("", title="Percent Wrong")
    percent_very_wrong: Optional[float] = Field("", title="Percent Very Wrong")
    percent_eval_failed: Optional[float] = Field("", title="Percent Eval Failed")
    rounds: int = Field(-1, title="Rounds")
    result: str = Field("", title="Result")


class EvalResultsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(EvalResult)
        coerce = True


class SessionResult(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True, protected_namespaces=())

    session_id: str = Field("", title="Session ID")
    session_time: str = Field("", title="Session Time")
    prompt_variation_id: str = Field("", title="Prompt Variation ID")
    model_configuration_id: str = Field("", title="Model Configuration ID")
    survey_id: str = Field("", title="Survey ID")
    question_id: str = Field("", title="Question ID")
    language: str = Field("", title="Language")
    question_number: int = Field(-1, title="Question No.")
    output: str = Field("", title="Response Text")
    grade: str = Field("", title="Grade")


class SessionResultsDf(pa.DataFrameModel):
    class Config:
        dtype = PydanticModel(SessionResult)
        coerce = True
