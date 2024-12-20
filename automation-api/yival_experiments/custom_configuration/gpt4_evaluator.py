"""
OpenAIPromptBasedEvaluator is an evaluator that uses OpenAI's prompt-based
system for evaluations.

The evaluator interfaces with the OpenAI API to present tasks and interpret
the model's responses to determine the quality or correctness of a given
experiment result.
"""
import copy
import logging

import litellm
from evaluator_common import (
    CLASSIFY_STR,
    calculate_choice_score,
    choices_to_string,
    completion_with_backpff,
    extract_choice_from_response,
    format_template,
)
from gpt4_evaluator_config import GPT4EvaluatorConfig
from yival.evaluators.base_evaluator import BaseEvaluator
from yival.schemas.evaluator_config import (
    EvaluatorOutput,
    EvaluatorType,
    MethodCalculationMethod,
    MetricCalculatorConfig,
)
from yival.schemas.experiment_config import (
    ExperimentResult,
    InputData,
    MultimodalOutput,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPT4Evaluator(BaseEvaluator):
    """Evaluator using OpenAI's prompt-based evaluation."""

    default_config = GPT4EvaluatorConfig(name="gpt4_evaluator")  # type: ignore

    def __init__(self, config: GPT4EvaluatorConfig):
        super().__init__(config)
        self.config = config

    def evaluate(self, experiment_result: ExperimentResult) -> EvaluatorOutput:
        """Evaluate the experiment result using OpenAI's prompt-based evaluation."""
        format_dict = copy.deepcopy(experiment_result.input_data.content)
        format_dict["raw_output"] = experiment_result.raw_output.text_output

        prompt = format_template(self.config.prompt, format_dict)
        if isinstance(prompt, str):
            prompt = [{"role": "user", "content": prompt}]

        prompt[-1]["content"] += "\n\n" + CLASSIFY_STR.format(
            choices=choices_to_string(self.config.choices)
        )
        response = completion_with_backpff(
            model=self.config.model_name,
            messages=prompt,
            temperature=0.0,
            n=1,
            max_tokens=2000,
            request_timeout=60,
            caching=True,
        )
        # response = openai.ChatCompletion.create(
        #     model="gpt-4", messages=prompt, temperature=0.5)
        response_content = response["choices"][0]["message"]["content"]
        choice = extract_choice_from_response(response_content, self.config.choices)
        score = calculate_choice_score(choice, self.config.choice_scores)
        return EvaluatorOutput(
            name=self.config.name,
            result=score if score is not None else choice,
            display_name=self.config.display_name,
            metric_calculators=self.config.metric_calculators,
        )


BaseEvaluator.register_evaluator("gpt4_evaluator", GPT4Evaluator, GPT4EvaluatorConfig)


def main():
    """Main function to test the OpenAIPromptBasedEvaluator."""
    from example_evaluator_data import (
        choice_scores,
        choices,
        content,
        prompt,
        raw_output,
    )

    litellm.set_verbose = True

    evaluator_config = GPT4EvaluatorConfig(
        name="gpt4_evaluator",
        display_name="correctness test",
        metric_calculators=[
            MetricCalculatorConfig(
                MethodCalculationMethod(MethodCalculationMethod.AVERAGE)
            )
        ],
        prompt=prompt,
        choices=choices,
        evaluator_type=EvaluatorType.INDIVIDUAL,
        choice_scores=choice_scores,
    )
    input_data_example = InputData(content=content)

    experiment_result_example = ExperimentResult(
        input_data=input_data_example,
        combination={"wrapper1": "var1", "wrapper2": "var2"},
        raw_output=MultimodalOutput(text_output=raw_output),
        latency=150.0,
        token_usage=50,
    )

    evaluator = GPT4Evaluator(evaluator_config)
    result = evaluator.evaluate(experiment_result_example)
    print("Result: ", result.result)


if __name__ == "__main__":
    main()
