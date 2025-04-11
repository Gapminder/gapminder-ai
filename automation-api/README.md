# Gapminder AI Benchmark tool

This is a set of libraries which help to run experiments for the Gapminder AI worldview benchmark[1] project.

[1]: https://www.gapminder.org/ai

## The Experiment Configurations

We rely on a external Google Spreadsheet for all the questions/prompt variations/models/evaluators configurations.

The tool expected following sheets in the experiment config:

- Questions
- Question options
- Prompt Variations
- Metrics
- Evaluators
- Models
- Model configurations
- Latest Results

Please refer to the current configuration spreadsheet[2] for the expected columns for each sheet.

[2]: https://docs.google.com/spreadsheets/d/1Tsa4FDAP-QhaXNhfclqq2_Wspp32efGeZyGHxSrtRvA/edit?gid=42711988#gid=42711988

## How to run an experiment

### perpare the environment

0. make sure python and poetry installed
1. clone this repo
2. enable the automation-api environment by issuing `poetry shell`
3. add an .env file `cp .env.example .env`, and edit `.env` properly.

### running experiment in Notebook

refer to run_evaluation.py[3] for a demo.

[3]: https://github.com/Gapminder/gapminder-ai/blob/253c2b79aef96a5445bd82171e4d11fce488a8c1/automation-api/notebooks/run_evaluation.py

### running experiment in CLI

Below instruction is a demo for running evaluation for a model with ID `mc049` using all questions and metrics.

- run `python -m lib.pilot.generate_experiment --output-dir .` to download all configurations from AI Eval spreadsheet into a subfolder named using timestamp in current dir
- cd to the subfolder just created
- run `python -m lib.pilot.generate_prompts --model-config-id mc049` to generate prompts for mc049 (mc049-question_prompts.jsonl)
- run `python -m lib.pilot.send_batch_prompt mc049-question_prompts.jsonl --method openai` to send the batch to openai, or use `--method vertex` for Vertex, `--method anthropic` for Anthropic. Add `--wait` to wait until the response is ready. (filename will be mc049-question_prompts-response.jsonl)
- run `python -m lib.pilot.generate_eval_prompts mc049-question_prompts-response.jsonl` to generate eval prompts, this will create multiple files based on the parameters listed in the Evaluator sheet in AI Eval spreadsheet.
  - There is `--send` parameter to send them right away.
  - If you didn't use `--send`, then you need to run send_batch_prompt for each generated eval prompts. note that for vertex endpoints we need to provide the `--model-id` parameter to set the target model. Because vertex jsonl format doesn't include model id.
- and finally, run `python -m lib.pilot.summarize_results` to create summarized output. (you can find some example data in the [test folder](https://github.com/Gapminder/gapminder-ai/tree/batch_processing/automation-api/tests/pilot/data/example_batch))

you can use `-h` to view cli options for the modules.

Currently I only keep the final outputs and the configurations from AI Eval spreadsheet in the [experiment folder.](https://github.com/Gapminder/gapminder-ai/tree/batch_processing/experiments). The master output csv files are also available in [ai worldview benchmark dataset](https://github.com/open-numbers/ddf--gapminder--ai_worldview_benchmark/tree/master/etl/source/results).

## schema changes in AI Eval Spreadsheet

- added "Evaluators": [link](https://docs.google.com/spreadsheets/d/1Tsa4FDAP-QhaXNhfclqq2_Wspp32efGeZyGHxSrtRvA/edit?gid=168651435#gid=168651435), which contains the configurations for evaluator models
- removed "Latest Results", because we move the files to another dataset
- in "Model Configurations", added `Name` column. Because we will be testing the same LLM with different parameters. So we should put a Name for Model configuration
- in "Models": added `Model Publish Date`.

## Development

See [./DEV.md]().

## TODOs
- create an all-in-one cli tool so that we don't need to type long commands
- create a module for handling errors in batch responses. (it has been written in the run_evaluation notebook)

