# How to run experiment

## 1. Install automation-api library dependencies

``` shell
cd /path/to/gapminder-ai/automation-api
poetry install
```

## 2. Enable poetry shell

``` shell
poetry shell
```

## 3. Fetch questions

``` shell
poe fetch_questions
```

This will fetch all enabled questions in the AI eval spreadsheet and create data/questions_{language}.csv files, one per language.

Note: Yival requires a dataset to have a local file when the source type is set to "dataset". So we need to fetch it first.

## 4. Generate experiment config

To generate experiment configuration based on the current settings in the AI Eval Spreadsheet:

``` shell
poe generate_experiment_config
```

This generates one experiment configuration per language and stores them in `./yival_experiments/experiment_configurations/`.

## 5. Start Redis for caching

The model compare function will cache LLM call results for the
evaluator, and by default the cache is dictionary in memory.
Redis is used by default for caching, so that it won't lose the cache when Yival
exits. start a local redis server:

``` shell
poe start_redis
```

Note: To not use Redis, comment the line for redis cache in the top
of `custom_configuration/model_compare.py` and

## 6. Run an experiment

To run a particular experiment configuration (in `./yival_experiments/experiment_configurations/`):

``` shell
poe run_experiment --experiment=experiment_name
```

This will use the configuration experiment_name.yaml in `./yival_experiments/experiment_configurations/`
and output a pickle file in `./yival_experiments/output/experiment_name_en-US_0.pkl` which includes all Experiment Results objects.

When the experiment is completed, Yival will start a web server to show the results.

### Setup environment variables
Here are a list of environment variables that needed to be set (in automation-api/.env file) before running experiments, depending on the model we are testing:

- OpenAI models: OPENAI_API_KEY and OPENAI_ORG_ID
- Hugging Face models: HUGGINGFACEHUB_API_TOKEN
- Replicate models: REPLICATE_API_KEY
- Alibaba models: DASHSCOPE_API_KEY
- Google Gemini API: GEMINI_API_KEY
- VertexAI models: VERTEX_SERVICE_ACCOUNT_CREDENTIALS, VERTEXAI_PROJECT and VERTEXAI_LOCATIONS

Some notes on VertexAI:

- VERTEXAI_LOCATIONS can be a comma separated list of gcp regions, to get over the limit of 5 requests per minute of Gemini
- follow the instruction in [DEV.md](https://github.com/Gapminder/gapminder-ai/blob/main/automation-api/DEV.md#obtaining-developer-specific-service-account-credentials-base64-encoded) to obtain VERTEX_SERVICE_ACCOUNT_CREDENTIALS

## 7. Generate a result xlsx from output

To convert the pickle files to Excel file:

``` shell
poe generate_result
```

This will read all pickles in output/ directory and will generate `results.xlsx` in output/ directory.

TODO: We can add a custom evaluator in Yival to calculate the final scores.

## 8. Calculate scores, upload results to AI Eval Spreadsheet

Two notebooks in `./yival_experiments/notebooks/` directory are provided for calculating scores.

- upload_to_ai_eval_sheet.py: generate the result table and upload to the `Latest Results` sheet in AI Eval Spreadsheet
- result_data_analysis.py: compute statistics from the results

Start Jupyter:

```shell
poe notebooks
```

Then open the notebooks in the browser and run them.
