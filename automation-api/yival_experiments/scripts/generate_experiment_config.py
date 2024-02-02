import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from lib.ai_eval_spreadsheet.schemas import PromptVariation
from lib.ai_eval_spreadsheet.wrapper import AiEvalData
from lib.pilot.helpers import (
    ModelAndConfig,
    get_metrics,
    get_model_configs,
    get_prompt_variants,
    load_model_parameters,
    read_ai_eval_spreadsheet,
)

current_script_path = Path(__file__).parent

# to make pyyaml's dumper generate good looking strings
# https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
# -

base_configs_path = current_script_path / "../experiment_defaults.yaml"
experiment_configurations_path = current_script_path / "../experiment_configurations/"
latest_experiment_path = current_script_path / "../experiment_latest.yaml"


def get_evaluators(ai_eval_sheet: AiEvalData):
    metrics = get_metrics(ai_eval_sheet)
    res = list()
    for m in metrics:
        metric: Dict[str, Any] = dict()
        metric["evaluator_type"] = "individual"
        metric["metric_calculators"] = [{"method": "AVERAGE"}]
        metric["name"] = "gpt4_evaluator"
        metric["model_name"] = "gpt-4"
        metric["prompt"] = m.prompt
        metric["choices"] = m.choices.split(", ")
        metric["description"] = m.description
        metric["choice_scores"] = dict(
            zip(m.choices.split(", "), map(int, m.choice_scores.split(", ")))
        )
        metric["scale_description"] = "{}-{}".format(
            m.choice_scores[0], m.choice_scores[-1]
        )
        metric["display_name"] = m.name
        res.append(metric)

    return res


def get_model_variations_yaml_dict(model_configs: List[ModelAndConfig]):
    res: Dict[str, Any] = dict()
    res["name"] = "model_config"
    res["generator_name"] = "model_config_generator"
    variant_list = list()
    for model, config in model_configs:
        for t in range(config.repeat_times):
            model_dict = dict()
            model_dict["vendor"] = model.vendor
            model_dict["model_id"] = model.model_id
            model_dict["params"] = load_model_parameters(config.model_parameters)
            model_dict["round"] = t + 1
            variant_list.append(model_dict)

    res["generator_config"] = {"models": variant_list}
    return res


def get_prompt_variations_yaml_dict(prompt_variations: List[PromptVariation]):
    res: Dict[str, Any] = dict()
    res["name"] = "prompt_template"
    variant_list = list()
    for p in prompt_variations:
        variant_dict = dict()
        variant_dict["variation_id"] = p.variation_id
        variant_dict["value_type"] = "str"
        value = p.question_prompt_template.format(question=p.question_template)
        variant_dict["instantiated_value"] = value
        variant_dict["value"] = value
        variant_list.append(variant_dict)

    res["variations"] = variant_list
    return res


def main():
    print("Reading AI eval spreadsheet")
    sheet = read_ai_eval_spreadsheet()
    # load default config
    config = yaml.load(open(base_configs_path, "r"), Loader=yaml.Loader)

    # metrics
    config["evaluators"] = get_evaluators(sheet)
    # model configs and prompt variations
    model_configs = get_model_configs(sheet)
    model_ids = {model.model_id for model, model_config in model_configs}
    prompt_variations = get_prompt_variants(sheet)
    prompt_variation_languages = {
        prompt_variation.language for prompt_variation in prompt_variations
    }

    experiment_names = []
    for model_id in model_ids:
        model_id_specific_model_configurations = [
            (model, model_config)
            for model, model_config in model_configs
            if model.model_id == model_id
        ]
        model_configs_yaml_dict = get_model_variations_yaml_dict(
            model_id_specific_model_configurations
        )

        for prompt_variation_language in prompt_variation_languages:

            # filter out prompt variations that are not in the current language
            language_specific_prompt_variations = [
                prompt_variation
                for prompt_variation in prompt_variations
                if prompt_variation.language == prompt_variation_language
            ]

            # compile the configuration
            prompt_variations_yaml_dict = get_prompt_variations_yaml_dict(
                language_specific_prompt_variations
            )
            config["variations"] = [
                model_configs_yaml_dict,
                prompt_variations_yaml_dict,
            ]
            config["dataset"][
                "file_path"
            ] = f"data/questions_{prompt_variation_language}.csv"

            # create configuration yaml file
            os.makedirs(experiment_configurations_path, exist_ok=True)
            now = datetime.now()
            yival_sanitized_model_id = model_id.replace("/", "_").replace(".", "-")
            experiment_name = f'experiment_{now.strftime("%Y%m%d%H%M")}_{yival_sanitized_model_id}_{prompt_variation_language}'
            file_name = f"{experiment_name}.yaml"
            output_file = experiment_configurations_path / file_name
            with open(output_file, "w") as f:
                yaml.dump(config, stream=f, sort_keys=False, allow_unicode=True)
                f.close()
            experiment_names.append(experiment_name)

    print(
        f"Experiment configurations saved to {experiment_configurations_path}. To run them:"
    )
    for experiment_name in experiment_names:
        print(f"  poe run_experiment --experiment={experiment_name}")


if __name__ == "__main__":
    main()
