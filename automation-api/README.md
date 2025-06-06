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

### Notes on model ids

Model configurations should use provider prefixes in the `model_id` field:
- `openai/gpt-4` → OpenAI provider
- `anthropic/claude-3` → Anthropic provider
- `vertex_ai/publishers/google/models/gemini-2.0-flash-001` → Vertex AI provider
- `deepseek/deepseek-reasoner` → deepseek provider
- `alibaba/qwen-3` → OpenAI-compatible provider (different API key/URL)

Generally the model id scheme will follow the conventions used in Litellm. with the exception of:

- vertex_ai: we need to put the entire model id containing publishers paths e.g. `vertex_ai/publishers/google/models/gemini-2.0-flash-001`
- some custom openai-compatible models: currently we use `alibaba/` prefix for alibaba models.

## How to run an experiment

### prepare the environment

0. make sure python and [uv](https://github.com/astral-sh/uv) installed
1. clone this repo
2. create and enable a virtual environment:
   ```
   cd automation-api
   uv venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   uv pip install -e .
   ```
3. add an .env file `cp .env.example .env`, and edit `.env` properly.
4. If using redis for litellm cache, please make sure redis is installed and edit the REDIS_HOST/REDIS_PORT in .env

### running experiment in Notebook

refer to run_evaluation.py[3] for a demo.

[3]: https://github.com/Gapminder/gapminder-ai/blob/253c2b79aef96a5445bd82171e4d11fce488a8c1/automation-api/notebooks/run_evaluation.py

### Running Experiments with the gm-eval CLI Tool

The `gm-eval` command-line tool simplifies running experiments by providing a unified interface for all steps in the experiment workflow. After setting up your environment, you can use this tool to run experiments with a single command or execute individual steps as needed.

#### Installation

The tool is automatically installed when you set up the environment:

```bash
uv pip install -e .
```

#### Basic Usage

To see all available commands and options:

```bash
gm-eval --help
```

#### Running a Complete Experiment

Before running experiment, it's recommanded to create a folder to store the experiment configs and results. For example:

```bash
mkdir experiments && cd experiments
```

To run a complete experiment for a model configuration in one command:

```bash
gm-eval run --model-config-id mc049 --mode litellm
```

This will:
1. Download configurations from the AI Eval spreadsheet into current_dir/YYYYMMDD_HHMMSS/
2. Generate prompts for the specified model
3. Send the prompts to the specified provider
4. Generate and send evaluation prompts and wait for evaluation results

Run the above command multiple times if there are multiple model configurations to test.

After all experiments are complete, run the summarize command to create a summarized CSV file and a parquet file containing all responses data:

```bash
gm-eval summarize --input-dir YYYYMMDD_HHMMSS
```

#### Batch mode and Litellm mode

The gm-eval tool now supports two processing modes with automatic provider detection:

**Batch Mode:**
- Uses provider-specific batch APIs (OpenAI, Anthropic, Vertex AI, Mistral, Alibaba)
- Supports waiting for completion with `--wait`
- Automatically validates provider compatibility and suggests alternatives

**LiteLLM Mode:**
- Real-time processing through LiteLLM
- Supports all providers (especially those without batch APIs like DeepSeek)
- Supports concurrent processing with `--processes`

By default, the `run` command uses batch mode, which will send all prompts to the specified provider using Batch API. Batchjobs accepts the `--wait` flag to wait for the batch job to complete before continuing.

```bash
gm-eval run --model-config-id mc049 --mode batch --wait
```

The above command will send the batch to a provider and wait until it gets response file. If --wait flag is not set, it will return immediately after sending the batch. A .processing file with the batch ID will be created to indicate that the batch is still processing. You can run the same command with --wait flag to get the responses file later.

To use Litellm mode, add the `--mode litellm` flag, as shown in previous section.

#### other useful flags for gm-eval run

- `--output-dir`: Specify the output directory for generated prompts and responses (when used, it won't create a new timestamp directory)
- `--skip-download`: Skip downloading configurations
- `--skip-generate`: Skip generating question prompts, use existing prompts
- `--skip-send`: Skip sending the question prompts, use existing responses
- `--skip-evaluate`: Skip evaluating the results

#### Running Individual Steps

You can also run each step individually:

1. **Download configurations**:
   ```bash
   gm-eval download
   ```

   This creates a folder with timestamp format like `20250604_130353` and download the configurations into ai_eval_sheets/ dir.

2. **Generate prompts** (Optional - send command does this automatically):

for example the above step created a `20250604_130353/` dir, then:

   ```bash
   gm-eval generate --model-config-id mc049 --base-path 20250604_130353 --jsonl-format openai
   ```

**Note**: You can skip this step as the `send` command now automatically generates prompts with the correct format for the detected provider.

**available formats** (auto-detected by send command)

- openai: used for litellm, anthropic, openai models
- mistral: used for mistral models
- vertex: used for vertex_ai models

3. **Send prompts** (Enhanced - Recommended):
   ```bash
   gm-eval send --mode batch --model-config-id mc049 --output-dir 20250604_130353 --wait
   ```

   Or for LiteLLM mode:
   ```bash
   gm-eval send --mode litellm --model-config-id mc049 --output-dir 20250604_130353 --processes 2
   ```

   **Enhanced Features**: The `send` command now includes:
   - ✅ **Auto-generates prompts** if they don't exist (no separate generate step needed)
   - ✅ **Batch mode validation** - checks provider compatibility and suggests alternatives
   - ✅ **Smart format detection** - automatically uses correct format (openai/vertex/mistral) based on provider
   - ✅ **Force regeneration** - use `--force-regenerate` to recreate prompts when switching modes

   **Example Error Handling**:
   ```bash
   # If you try batch mode with an incompatible provider:
   $ gm-eval send --mode batch --model-config-id mc057  # DeepSeek model
   ❌ Provider 'deepseek' does not support batch mode.
   💡 Suggestion: Try using --mode litellm instead.
      Example: gm-eval send --mode litellm --model-config-id mc057
   ```

   **Send prompts** (Legacy file-based):
   ```bash
   gm-eval send-file 20250604_130353/mc049-question_prompts.jsonl --method openai --wait
   ```

4. **Generate and send evaluation prompts**:
   ```bash
   gm-eval evaluate 20250604_130353/mc049-question_prompts-response.jsonl --send --wait
   ```

   You will want to run this twice. First without the `--wait` to send all evaluator prompts,
   and then use `--wait` to download the results.

   **Note about batch mode**: When using methods other than "litellm" (such as "openai", "anthropic", etc.),
   you are using batch mode. In the `gm-eval run` command, the `--wait` flag affects the evaluation step.
   The send step will always wait for results to ensure the response file is available for the evaluate step.

   When using batch mode, you can stop the command with Ctrl+C while it's waiting for results and rerun it
   later with the same parameters to check if results are ready. This is useful for long-running batch jobs.

   **Important**: The `gm-eval run` command no longer automatically runs the summarize step. You must run
   `gm-eval summarize` separately after all your experiments are complete.

5. **Summarize results** (run this after all experiments are complete):
   ```bash
   gm-eval summarize --input-dir 20250604_130353
   ```

#### Advanced Options

Each command has additional options that can be viewed with the `--help` flag:

```bash
gm-eval run --help
gm-eval download --help
gm-eval generate --help
# etc.
```

Currently I only keep the final outputs and the configurations from AI Eval spreadsheet in the [experiment folder.](https://github.com/Gapminder/gapminder-ai/tree/batch_processing/experiments). The master output csv files are also available in [ai worldview benchmark dataset](https://github.com/open-numbers/ddf--gapminder--ai_worldview_benchmark/tree/master/etl/source/results).


### Additional Commands

#### Handling Failed Requests

The CLI provides two commands for managing failed API requests:

1. **Split failed requests**:
   ```bash
   gm-eval split --requests requests.jsonl --output failed-requests.jsonl
   ```
   - Extracts requests that resulted in errors from the responses file
   - Default response path is requests filename with '-response' suffix

2. **Merge responses**:
   ```bash
   gm-eval merge original.jsonl retry1.jsonl retry2.jsonl --output merged.jsonl
   ```
   - Combines multiple response files
   - Later files override earlier ones for duplicate custom_ids

## Development

See [./DEV.md]().

## TODOs
- when using --wait for `gm-eval evaluate`, the prompts are sent sequentially. So it must wait for first evaluator finish the batch before the second one can start. But we should send all batch at once.
