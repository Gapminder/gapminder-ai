import litellm
from litellm import completion
from llms.alibaba_complete import llm_complete as alibaba_llm_complete
from model_config_wrapper import ModelConfigWrapper
from yival.logger.token_logger import TokenLogger
from yival.schemas.experiment_config import MultimodalOutput
from yival.schemas.model_configs import Response
from yival.states.experiment_state import ExperimentState
from yival.wrappers.string_wrapper import StringWrapper

# load env vars
from lib.config import read_config
from llms.palm_completion import (
    safety_settings_new_categories,
    safety_settings_old_categories,
)

read_config()
# default model config if not provided
default_model_config = dict(model_name="gpt-3.5-turbo", params={"temperature": 0.5})
# set this to see verbose outputs
litellm.set_verbose = True
# enable caching in the evaluator.
# litellm.cache = litellm.Cache()
# to not use Redis for caching: uncomment the line above and comment the line below.
litellm.cache = litellm.Cache(type="redis", host="127.0.0.1", port=26379)


def model_compare(
    question_id: str,
    question_text: str,
    language: str,
    option_a: str,
    option_a_correctness: str,
    option_b: str,
    option_b_correctness: str,
    option_c: str,
    option_c_correctness: str,
    state: ExperimentState,
) -> MultimodalOutput:
    logger = TokenLogger()
    logger.reset()

    model = ModelConfigWrapper(
        default_model_config, name="model_config", state=state
    ).get_value()

    prompt_template_default = """Answer following multiple choices question:
    Question: {question_text}
    A. {option_a}
    B. {option_b}
    C. {option_c}

    Answer:"""
    # TODO: there might be better way to handle variables in prompt variations.
    prompt_template = str(StringWrapper("", name="prompt_template", state=state))
    if prompt_template == "":
        prompt_template = prompt_template_default

    prompt = prompt_template.format(
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
    )
    # system_prompt = """..."""

    if model["vendor"] == "Alibaba":
        # FIXME: alibaba's complete function doesn't support system prompt.
        output = alibaba_llm_complete(
            model_name=model["model_id"], prompt=prompt, **model["params"]
        )
        response = Response(output=output).output
        response_text = response["choices"][0]["message"]["content"]
    elif model["vendor"] == "Google":
        messages = [
            # {"content": system_prompt, "role": "system"},
            {"content": prompt, "role": "user"}
        ]
        try:
            response = Response(
                output=completion(
                    model=model["model_id"],
                    messages=messages,
                    # google allows changing content filters. We will disable all
                    safety_settings=safety_settings_old_categories
                    if model["model_id"].startswith("palm")
                    else safety_settings_new_categories,
                    caching=False,
                    num_retries=10,
                    request_timeout=60,
                    **model["params"],
                )
            ).output
            response_text = response["choices"][0]["message"]["content"]
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(str(e))
            response = None
            response_text = "No Answer. Reason:\n" + str(e)
    else:
        messages = [
            # {"content": system_prompt, "role": "system"},
            {"content": prompt, "role": "user"}
        ]
        response = Response(
            output=completion(
                model=model["model_id"],
                messages=messages,
                caching=False,
                num_retries=10,
                request_timeout=60,
                **model["params"],
            )
        ).output
        response_text = response["choices"][0]["message"]["content"]

    res = MultimodalOutput(
        text_output=response_text,
    )
    if type(response) is Response:
        token_usage = response["usage"]["total_tokens"]
        logger.log(token_usage)
    else:
        logger.log(0)
    return res


def main():
    q = "How many people worldwide have their basic needs met when it comes to food, "
    "water, toilets, electricity, schooling and healthcare?"
    print(
        model_compare(
            "1",
            q,
            "en_US",
            "Around 20%",
            "3",
            "Around 50%",
            "2",
            "Around 80%",
            "1",
            ExperimentState(),
        )
    )


if __name__ == "__main__":
    main()
