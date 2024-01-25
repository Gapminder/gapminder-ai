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

To update the experiment with the settings in AI Eval Spreadsheet, run the generate_experiment_config.py script.

``` shell
poe generate_experiment_config
```

This generates one experiment configuration per language and stores them in in `./yival_experiments/experiment_configurations/`.

## 5. Run an experiment

To run a particular experiment:

``` shell
yival run --output ./yival_experiments/output/experiment_20231104_en ./yival_experiments/experiment_20231104_en.yaml
```

This will output a pickle file in `output/experiment_20231104_en_0.pkl` which include all Experiment Results objects.

When the experiment is completed, Yival will start a web server to show the results.

### Use Redis for caching

The model compare function will cache LLM call results for the
evaluator, and by default the cache is dictionary in memory. You can
also use Redis to caching, so that it won't lose the cache when Yival
exits. To do this, uncomment the line for redis cache in the top of
`custom_configuration/model_compare.py` and set the host and password
to your redis server.

## 6. Generate a result xlsx from output

To convert the pickle files to Excel file:

``` shell
poe generate_results_file
```

This will read all pickles in output/ directory and will generate `results.xlsx` in output/ directory.

TODO: We can add a custom evaluator in Yival to calculate the final scores.

## 7. Calculate scores, upload results to AI Eval Spreadsheet

Two notebooks in notebooks/ directory are provided for calculating scores.

- final_scores.py: calculate a final score for each model and prompt
- upload_to_ai_eval_sheet.py: generate the result table and upload to the `Latest Results` sheet in AI Eval Spreadsheet
