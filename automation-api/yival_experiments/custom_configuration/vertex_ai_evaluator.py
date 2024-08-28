"""
An evaluator that uses Vertex AI's prompt-based system for evaluations.

The evaluator interfaces with the Vertex AI API to present tasks and interpret
the model's responses to determine the quality or correctness of a given
experiment result.
"""

import copy
import logging
import os

import litellm
from evaluator_common import (
    CLASSIFY_STR,
    calculate_choice_score,
    choices_to_string,
    completion_with_backpff,
    extract_choice_from_response,
    format_template,
)
from vertex_ai_evaluator_config import VertexAIEvaluatorConfig
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

# because claude opus is only available in one location, we will hard code it here.
VERTEX_LOCATION = "us-east5"


class VertexAIEvaluator(BaseEvaluator):
    """Evaluator using VertexAI's prompt-based evaluation."""

    default_config = VertexAIEvaluatorConfig(name="vertex_ai_evaluator")  # type: ignore

    def __init__(self, config: VertexAIEvaluatorConfig):
        super().__init__(config)
        self.config = config

    def evaluate(self, experiment_result: ExperimentResult) -> EvaluatorOutput:
        """Evaluate the experiment result using Vertex AI's prompt-based evaluation."""
        assert isinstance(self.config, VertexAIEvaluatorConfig)
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
            vertex_ai_location=VERTEX_LOCATION,
            vertex_ai_project=os.environ["VERTEXAI_PROJECT"],
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


BaseEvaluator.register_evaluator(
    "vertex_ai_evaluator", VertexAIEvaluator, VertexAIEvaluatorConfig
)


def main():
    """Main function to test the OpenAIPromptBasedEvaluator."""
    from example_evaluator_data import (
        choice_scores,
        choices,
        content,
        prompt,
        raw_output,
    )

    from lib.config import read_config

    read_config()
    litellm.set_verbose = True

    evaluator_config = VertexAIEvaluatorConfig(
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

    evaluator = VertexAIEvaluator(evaluator_config)
    result = evaluator.evaluate(experiment_result_example)
    print("Result: ", result.result)


if __name__ == "__main__":
    main()
