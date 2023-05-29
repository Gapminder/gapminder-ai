import json
from dataclasses import dataclass
from typing import List


@dataclass
class QuestionOption:
    letter: str
    option_text: str
    correctness: int

    def letter_and_text(self) -> str:
        return f"{self.letter}. {self.option_text}"


@dataclass
class Question:
    question_id: str
    question_text: str
    options: List[QuestionOption]
    correct_idx: int

    def correct_answer(self, letter_only: bool = False) -> str:
        ca = self.options[self.correct_idx]
        if letter_only:
            return ca.letter
        else:
            return ca.letter_and_text()


@dataclass
class PromptVariation:
    variation_id: str
    question_prompt_template: str
    followup_prompt_template: str

    def __post_init__(self):
        # convert 'nan' to ''
        # NOTE: nan (float) value has converted to 'nan' (string)
        # by the reader. That's why I am checking with 'nan' here.
        if self.followup_prompt_template == "nan":
            self.followup_prompt_template = ""


@dataclass
class ModelConfig:
    model_config_id: str
    vendor: str
    model_id: str
    model_parameters: str
    repeat_times: int

    def __post_init__(self):
        # convert model_parameters (json string) to dict
        # NOTE: nan (float) value has converted to 'nan' (string)
        # by the reader. That's why I am checking with 'nan' here.
        if self.model_parameters == "nan":
            self.model_parameters = {}
        else:
            self.model_parameters = json.loads(self.model_parameters)
