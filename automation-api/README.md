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
gm-eval run --model-config-id mc049 --method openai --wait
```

This will:
1. Download configurations from the AI Eval spreadsheet into current_dir/YYYYMMDD_HHMMSS/
2. Generate prompts for the specified model
3. Send the prompts to the specified provider
4. Generate and send evaluation prompts and wait for evaluation results
5. Summarize the results (only if --wait flag is specified)

**available methods**

- openai/anthropic/vertex/mistral: using this method will send the batch via Batch API for these providers.
- litellm: using this method will send the batch via litellm in realtime.

#### Running Individual Steps

You can also run each step individually:

1. **Download configurations**:
   ```bash
   gm-eval download
   ```

   This creates a folder with timestamp format like `20250604_130353`

2. **Generate prompts**:

for example the above step created a `20250604_130353/` dir, then:

   ```bash
   gm-eval generate --model-config-id mc049 --base-path 20250604_130353 --jsonl-format openai
   ```

Please make sure to use the correct format for each provider.

**available formats**

- openai: use this for litellm, anthropic, openai models
- mistral
- vertex

3. **Send prompts** (Mode-based - Recommended):
   ```bash
   gm-eval send --mode batch --model-config-id mc049 --output-dir 20250604_130353 --wait
   ```

   Or for LiteLLM mode:
   ```bash
   gm-eval send --mode litellm --model-config-id mc049 --output-dir 20250604_130353 --wait
   ```

   **Send prompts** (Legacy file-based):
   ```bash
   gm-eval send-file 20250604_130353/mc049-question_prompts.jsonl --method openai --wait
   ```

## Mode-Based Processing (New)

The gm-eval tool now supports two processing modes with automatic provider detection:

### Modes

- **batch**: Uses provider-specific batch APIs (OpenAI Batch, Anthropic Batch, Vertex AI Batch, etc.)
- **litellm**: Uses LiteLLM for real-time processing across multiple providers

### Automatic Provider Detection

Model configurations use provider prefixes in the `model_id` field:
- `openai/gpt-4` → OpenAI provider, batch mode
- `anthropic/claude-3` → Anthropic provider, batch mode
- `vertex_ai/publishers/google/models/gemini-2.0-flash-001` → Vertex AI provider, batch mode
- `deepseek/deepseek-reasoner` → LiteLLM mode
- `alibaba/qwen-3` → OpenAI-compatible provider (different API key/URL)

### Mode Behavior

**Batch Mode:**
- Removes provider prefixes from model names (e.g., `mistral/mistral-small` → `mistral-small`)
- Uses provider-specific batch APIs
- Supports waiting for completion with `--wait`

**LiteLLM Mode:**
- Preserves full model names with prefixes
- Real-time processing through LiteLLM
- Supports concurrent processing with `--processes`

### Updated Workflow

1. **Run entire workflow** (Recommended):
   ```bash
   gm-eval run --mode batch --model-config-id mc049 --wait
   ```

2. **Individual steps with mode**:
   ```bash
   # Download and generate (creates timestamped folder like 20250604_130353)
   gm-eval download
   gm-eval generate --model-config-id mc049 --base-path 20250604_130353

   # Send with automatic detection
   gm-eval send --mode batch --model-config-id mc049 --output-dir 20250604_130353 --wait

   # Evaluate with mode support
   gm-eval evaluate 20250604_130353/mc049-question_prompts-response.jsonl --mode batch --send --wait
   ```

4. **Generate and send evaluation prompts**:
   ```bash
   gm-eval evaluate 20250604_130353/mc049-question_prompts-response.jsonl --send --wait
   ```

   You will want to run this twice. First without the `--wait` to send all evaluator prompts,
   and then use `--wait` to download the results.

   **Note about batch mode**: When using methods other than "litellm" (such as "openai", "anthropic", etc.),
   you are using batch mode. In the `gm-eval run` command, the `--wait` flag only affects the evaluation step.
   The send step will always wait for results to ensure the response file is available for the evaluate step.

   When using batch mode, you can stop the command with Ctrl+C while it's waiting for results and rerun it
   later with the same parameters to check if results are ready. This is useful for long-running batch jobs.

5. **Summarize results**:
   ```bash
   gm-eval summarize --input-dir 20250604_130353
   ```

   NOTE: Please be sure not to use `.` for input-dir, otherwise the filename of output file will not
   contain the date in it.

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
- improve the file naming in summarize step. (see the note above)
