import os
from datetime import datetime
import yaml
from lib.pilot.helpers import (
    read_ai_eval_spreadsheet,
    get_metrics,
    get_model_configs,
    get_prompt_variants,
    load_model_parameters,
)
from lib.ai_eval_spreadsheet.wrapper import AiEvalData
from typing import Dict, Any


# to make pyyaml's dumper generate good looking strings
# https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)
# -

base_configs_path = "../experiment_defaults.yaml"
experiment_archive_path = "../experiment_archive/"
latest_experiment_path = "../experiment_latest.yaml"


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


def get_model_variations(ai_eval_sheet: AiEvalData):
    model_configs = get_model_configs(ai_eval_sheet)
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


def get_prompt_variations(ai_eval_sheet: AiEvalData):
    prompt_variations = get_prompt_variants(ai_eval_sheet)
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
    # load ai eval spreadsheet
    sheet = read_ai_eval_spreadsheet()
    # load default config
    config = yaml.load(open(base_configs_path, "r"), Loader=yaml.Loader)

    # metrics
    config["evaluators"] = get_evaluators(sheet)
    # model configs and prompts
    config["variations"] = [get_model_variations(sheet), get_prompt_variations(sheet)]

    # create archive
    os.makedirs(experiment_archive_path, exist_ok=True)
    now = datetime.now()
    file_name = os.path.join(
        experiment_archive_path, "experiment_{}.yaml".format(now.strftime("%Y%m%d%H%M"))
    )

    with open(file_name, "w") as f:
        yaml.dump(config, stream=f, sort_keys=False, allow_unicode=True)
        print("experiment saved to", file_name)
        f.close()

    # also create one for latest experiment
    with open(latest_experiment_path, "w") as f:
        yaml.dump(config, stream=f, sort_keys=False, allow_unicode=True)
        print("experiment saved to", latest_experiment_path)
        f.close()


if __name__ == "__main__":
    main()
