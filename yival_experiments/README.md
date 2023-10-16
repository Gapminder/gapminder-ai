# How to run experiment

## 1. install automation-api library

``` shell
cd /path/to/gapminder-ai/automation-api
poetry install
```

## 2. enable poetry shell

``` shell
poetry shell
```

## 3. copy .env and fetch questions

``` shell
cd ../yival_experiment/
cp ../automation-api/.env ./

python fetch_question.py
```

This will fetch all enabled questions in the AI eval spreadsheet and create data/questions.csv.

Note: I tried to create a custom data reader to read data from AI eval
spreadsheet directly, but then yival failed to run the experiment. I
checked and found that Yival requires a dataset to have a local
file when the source type is set to "dataset". So we need to fetch it first.

(Maybe, we can solve it by changing the source type to "machine generated")

## 4. run the experiment

The full experiment configuration is [here](https://github.com/Gapminder/gapminder-ai/blob/yival/yival_experiments/experiment.yaml)

``` shell
yival run --output ./output experiment.yaml
```

This will output a pickle file in output/ which include all Experiment Results objects.

Note: After running the experiment, Yival normaly will run a web
server to show the results. But somehow it doesn't start a web server
for our experiment. It just exits, though it is able to save the
outputs to a pickle file.

## 5. generate a result csv from output

Because of above issue, I created a script to generate a summary table:

``` shell
cd output
python generate_result.py
```

This will generate a `results.csv` file in the output directory.
