from yival.common.model_utils import llm_completion
from yival.logger.token_logger import TokenLogger
from yival.schemas.experiment_config import MultimodalOutput
from yival.schemas.model_configs import Request, Response
from yival.states.experiment_state import ExperimentState
from yival.wrappers.string_wrapper import StringWrapper
from model_config_wrapper import ModelConfigWrapper
from llms.alibaba_complete import llm_complete as alibaba_llm_complete
from llms.palm_completion import safety_settings
from litellm import completion

# load env vars
from lib.config import read_config

read_config()


default_model_config = dict(model_name="gpt-3.5-turbo", params={"temperature": 0.5})


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
    # NOTE: we can use template in StringWrapper.
    # str(
    # StringWrapper(
    #     template="""
    #     Generate a landing page headline for {tech_startup_business}
    #     """,
    #     variables={
    #         "tech_startup_business": tech_startup_business,
    #     },
    #     name="task"
    #     )
    # )
    prompt_template = str(StringWrapper("", name="prompt_template", state=state))
    if prompt_template == "":
        prompt_template = prompt_template_default

    prompt = prompt_template.format(
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
    )

    if model["vendor"] == "Alibaba":
        output = alibaba_llm_complete(
            model_name=model["model_id"], prompt=prompt, **model["params"]
        )
        response = Response(output=output).output
    elif model["vendor"] == "Google":
        # google allows changing content filters. We will disable all
        messages = [{"content": prompt, "role": "user"}]
        response = Response(
            output=completion(
                model=model["model_id"],
                messages=messages,
                safety_settings=safety_settings,
            )
        ).output
        # print(response)
    else:
        response = llm_completion(
            Request(model_name=model["model_id"], prompt=prompt, params=model["params"])
        ).output

    res = MultimodalOutput(
        text_output=response["choices"][0]["message"]["content"],
    )
    # print(response["choices"][0]["message"]["content"])
    token_usage = response["usage"]["total_tokens"]
    logger.log(token_usage)
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
            3,
            "Around 50%",
            2,
            "Around 80%",
            1,
            ExperimentState(),
        )
    )


if __name__ == "__main__":
    main()
