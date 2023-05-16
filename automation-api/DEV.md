## Development

### Setting up the development environment

First, install Python 3.9 and [Poetry](https://python-poetry.org/) on your system.

Then, install dependencies:

```
poetry install
```

This sets up a local Python environment with all the relevant dependencies, including the Development Tools listed further down in this readme.

The remaining commands in this readme assume you have activated the local Python environment by running:

```
poetry shell
```

Now install the Git hooks that will make it harder to accidentally commit incorrectly formatted files:

```
pre-commit install
```

## Local Configuration

Initialize the local configuration file:

```shell
cp .env.example .env
```

Configure the environment variables in `.env` as per the configuration sections below.

### For deploying to production

- `GCP_PROJECT` - GCP project id to use for deployment.
- `GCP_REGION` - GCP region to use for deployment.

### For running in production

- `OPENAI_API_KEY` - An OpenAI API key to use for OpenAI model evaluations in production
- `OPENAI_ORG_ID` - The OpenAI organization id to use for billing purposes

### For local development

The deployed cloud functions will use the access credentials of the current user and operate on the spreadsheet that is currently opened. During local development, we have neither active credentials or an open spreadsheet, so the following additional configuration is necessary:

- `OPENAI_API_DEV_KEY` - An OpenAI API key to use for OpenAI model evaluations when running locally
- `SERVICE_ACCOUNT_CREDENTIALS` - Service account credentials, base64-encoded, native to the above GCP project (see below for instructions on how to obtain these)
- `GS_AI_EVAL_SPREADSHEET_ID` - Spreadsheet ID of the production AI Eval Spreadsheet (Note: the service account needs access to this spreadsheet)
- `GS_AI_EVAL_DEV_SPREADSHEET_ID` - Spreadsheet ID of a development copy of the AI Eval Spreadsheet (Note: the service account needs access to this spreadsheet)

## Cloud Configuration

Note: This has already been configured for our production GCP project, but instructions are supplied here to be able to set up a new project, e.g. for testing purposes or similar.

1. Use the [GCP API Dashboard](https://console.cloud.google.com/apis/dashboard) to enable the Google APIs necessary for the automation API (some of which may require billing to be enabled in the GCP project):
- [Google Sheets API](https://console.cloud.google.com/marketplace/product/google/sheets.googleapis.com)
- [Google Drive API](https://console.cloud.google.com/marketplace/product/google/drive.googleapis.com)
- [Secret Manager API](https://console.cloud.google.com/marketplace/product/google/secretmanager.googleapis.com) (requires billing to be enabled)
- [Cloud Functions API](https://console.cloud.google.com/marketplace/product/google/cloudfunctions.googleapis.com)
- [Cloud Build API](https://console.cloud.google.com/marketplace/product/google/cloudbuild.googleapis.com) (requires billing to be enabled)
- [IAM Service Account Credentials API](https://console.cloud.google.com/marketplace/product/google/iamcredentials.googleapis.com)

2. Create a new service account [here](https://console.cloud.google.com/iam-admin/serviceaccounts/create) called "Automation", id "automation", description "Used for automation processes" (there is no need to do anything for the option steps 2 and 3, just click done after Step 1).

### Obtaining Developer-specific service account credentials, base64-encoded

- Click on the service account in the listing [here](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Switch to the "KEYS" tab
- Click `Add key` -> `Create new key` -> Choose `JSON` key type - This will trigger a download of the JSON credentials
- On a Mac, run the following script to base64-encode, remove newlines and put the result in the clipboard:
```bash
cat path/to/file.json | openssl base64 | tr -d '\n' | pbcopy
```
- Paste the contents of the clipboard to `.env` where the `SERVICE_ACCOUNT_CREDENTIALS` environment variable is configured.

### Using a notebook environment for experimentation

Run the following to install a Jupyter kernel and opening the exploration Jupyter notebook:

```
poe install_kernel
jupyter-notebook notebooks/exploration-notebook.py
```

After selecting the `gapminder-ai-automation-api` kernel in Jupyter you should be able to import files from `lib`, e.g.:

```
from lib.config import read_config()
read_config()
```

### Installing new dependencies added by collaborators

When new dependencies gets added/updated/removed (in `pyproject.toml`) by collaborators, you need to run the following to install the latest dependencies:

```
poetry install
```

### Run tests, formatters and linters

Run tests, formatters and linters (using the currently active Python version):

```
poe test
```

#### Tests package

The package tests themselves are _outside_ of the main library code, in
the directory aptly named `tests`.

#### Running tests only

Run tests:

```
poe pytest
```

Run a specific test:

```
pytest tests/test_lib_import_statement.py
```

### Development setup

#### Principles

* Simple for developers to get up-and-running (`poetry`, `poethepoet`)
* Unit tests with test coverage reports (`pytest`)
* Consistent style (`ruff`, `black`)
* Prevent use of old Python syntax (`pyupgrade`)
* Require type hinting (`mypy`)

#### Development tools

* [`poetry`](https://python-poetry.org/) for dependency management
* [`poethepoet`](https://github.com/nat-n/poethepoet) as local task runner
* [`ruff`](https://beta.ruff.rs/docs/), [`black`](https://github.com/psf/black) and [`pyupgrade`](https://github.com/asottile/pyupgrade) for linting
* [`mypy`](https://mypy.readthedocs.io/en/stable/) for type hinting
* [`pre-commit`](https://pre-commit.com/) to run linting / dependency checks
* [`pytest`](https://docs.pytest.org/) to run tests
* [GitHub Actions](https://github.com/features/actions) for running tests in CI
* [`editorconfig`](https://editorconfig.org/) for telling the IDE how to format tabs/newlines etc
