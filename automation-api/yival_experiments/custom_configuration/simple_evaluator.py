"""
This module defines the SimpleEvaluator class, which is used for
evaluating string expected results.

Classes:
    SimpleEvaluator: Class for evaluating string expected
    results.

"""

import logging

from fuzzywuzzy import fuzz
from pydantic import BaseModel
from simple_evaluator_config import SimpleEvaluatorConfig
from yival.evaluators.base_evaluator import BaseEvaluator
from yival.schemas.evaluator_config import (
    EvaluatorOutput,
    ExpectedResultEvaluatorConfig,
)
from yival.schemas.experiment_config import ExperimentResult

logger = logging.getLogger("test")


# FIXME: move this class to the lib module.
class ExperimentInput(BaseModel):
    question_id: str
    question_text: str
    language: str
    option_a: str
    option_a_correctness: str
    option_b: str
    option_b_correctness: str
    option_c: str
    option_c_correctness: str

    class Config:
        population_by_name = True


def get_answers_dict(x: ExperimentInput) -> dict:
    mapping = {"Correct": 1, "Wrong": 2, "Very Wrong": 3}
    tpl = list(
        zip(
            [x.option_a, x.option_b, x.option_c],
            [x.option_a_correctness, x.option_b_correctness, x.option_c_correctness],
        )
    )
    tpl.sort(key=lambda x: mapping[x[1]])
    return {
        "correct_answer": tpl[0][0],
        "wrong_answer": tpl[1][0],
        "very_wrong_answer": tpl[2][0],
    }


def evaluate_text(input_string, correct_answer, wrong_answer, very_wrong_answer):
    """Grade the result by fuzzy matching the answers."""
    # Set a threshold for fuzzy matching
    threshold = 95

    # Function to check if a string contains an answer
    def contains_answer(text, answer):
        return fuzz.partial_ratio(text.lower(), answer.lower()) >= threshold

    # Check for each answer type
    has_correct = contains_answer(input_string, correct_answer)
    has_wrong = contains_answer(input_string, wrong_answer)
    has_very_wrong = contains_answer(input_string, very_wrong_answer)

    # Count how many answer types are present
    answer_count = sum([has_correct, has_wrong, has_very_wrong])

    # Evaluate based on the conditions
    if answer_count == 1:
        if has_correct:
            return 3
        elif has_wrong:
            return 2
        elif has_very_wrong:
            return 1

    # Return 0 if no answers or multiple answers are present
    return 0


class SimpleEvaluator(BaseEvaluator):
    """
    Class for evaluating string expected results.

    This class extends the BaseEvaluator and provides specific implementation
    for evaluating string expected results using different matching techniques.

    Attributes:
        config (ExpectedResultEvaluatorConfig): Configuration object for the
                                                evaluator.

    """

    default_config = SimpleEvaluatorConfig(name="simple_evaluator")

    def __init__(self, config: SimpleEvaluatorConfig):
        """
        Initialize the SimpleEvaluator with the provided
        configuration.

        Args:
            config (ExpectedResultEvaluatorConfig): Configuration object for
            the evaluator.

        """
        super().__init__(config)
        self.config: SimpleEvaluatorConfig = config

    def evaluate(self, experiment_result: ExperimentResult) -> EvaluatorOutput:
        """
        Evaluate the expected result against the actual result using the
        specified matching technique.

        Returns:
            EvaluatorOutput: An EvaluatorOutput object containing the
            evaluation result.

        """
        input_data = ExperimentInput(**experiment_result.input_data.content)
        raw_output = experiment_result.raw_output.text_output
        answer_dict = get_answers_dict(input_data)
        result = evaluate_text(raw_output, **answer_dict)
        return EvaluatorOutput(
            name=self.config.name,
            display_name="matching",
            result=result,
            metric_calculators=self.config.metric_calculators,
        )


BaseEvaluator.register_evaluator(
    "simple_evaluator", SimpleEvaluator, ExpectedResultEvaluatorConfig
)


def main():

    from example_evaluator_data import (
        content,
        raw_output,
    )
    from yival.schemas.experiment_config import (
        ExperimentResult,
        InputData,
        MultimodalOutput,
    )

    input_data_example = InputData(content=content)
    experiment_result_example = ExperimentResult(
        input_data=input_data_example,
        combination={"wrapper1": "var1"},
        raw_output=MultimodalOutput(text_output=raw_output),
        latency=150.0,
        token_usage=40,
    )

    evaluator_config = SimpleEvaluatorConfig(name="simple_evaluator")
    evaluator = SimpleEvaluator(evaluator_config)
    result = evaluator.evaluate(experiment_result_example)
    print("Result: ", result.result)


if __name__ == "__main__":
    main()
