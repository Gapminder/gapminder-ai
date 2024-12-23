import os
from datetime import datetime
from typing import Dict

import pandas as pd
from pandera.errors import SchemaError

from lib.ai_eval_spreadsheet.wrapper import (
    AiEvalData,
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
    sheet_names,
)
from lib.app_singleton import AppSingleton
from lib.authorized_clients import get_service_account_authorized_clients
from lib.config import read_config

logger = AppSingleton().get_logger()


def filter_included_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter dataframe to keep only rows where include_in_next_evaluation is True
    and remove the include_in_next_evaluation column
    """
    if 'include_in_next_evaluation' in df.columns:
        filtered_df = df[df['include_in_next_evaluation'] == True].copy()
        filtered_df.drop(columns=['include_in_next_evaluation'], inplace=True)
        return filtered_df
    return df

def read_ai_eval_spreadsheet() -> AiEvalData:
    config = read_config()
    authorized_clients = get_service_account_authorized_clients()
    ai_eval_spreadsheet_id = config["AI_EVAL_DEV_SPREADSHEET_ID"]
    ai_eval_spreadsheet = get_ai_eval_spreadsheet(
        authorized_clients, ai_eval_spreadsheet_id
    )
    try:
        return read_ai_eval_data(ai_eval_spreadsheet)
    except SchemaError as err:
        logger.error("DataFrame validation failed. Errors:", err.check)
        logger.error("Schema:")
        logger.error(err.schema)
        logger.error("Failure cases:")
        logger.error(err.failure_cases)  # dataframe of schema errors
        logger.error("Original data:")
        logger.error(err.data)  # invalid dataframe
        raise Exception("Data validation. Please fix and retry")


def save_sheets_as_csv() -> Dict[str, str]:
    """
    Fetches all sheets from the AI Eval Spreadsheet and saves them as CSV files.

    Returns:
        Dict mapping sheet names to their saved file paths
    """
    # Create experiments directory with today's date
    date_str = datetime.now().strftime("%Y%m%d")
    base_dir = os.path.join("experiments", date_str)
    os.makedirs(base_dir, exist_ok=True)

    # Read all data using existing wrapper
    ai_eval_data = read_ai_eval_spreadsheet()

    # Create evaluators DataFrame
    evaluators_data = {
        'evaluator': [
            'vertex_ai/gemini-1.5-pro-002',
            'gpt-4o-2024-11-20',
            'anthropic/claude-3-5-sonnet-202401022'
        ]
    }
    evaluators_df = pd.DataFrame(evaluators_data)

    # Map of editors to their corresponding sheet names and apply filtering
    editor_map = {
        "evaluators": evaluators_df,
        "questions": filter_included_rows(ai_eval_data.questions.data.df),
        "question_options": filter_included_rows(ai_eval_data.question_options.data.df),
        "prompt_variations": filter_included_rows(ai_eval_data.prompt_variations.data.df),
        "gen_ai_models": filter_included_rows(ai_eval_data.gen_ai_models.data.df),
        "gen_ai_model_configs": filter_included_rows(ai_eval_data.gen_ai_model_configs.data.df),
        "metrics": filter_included_rows(ai_eval_data.metrics.data.df),
        # no need to export the results
        # "evaluation_results": ai_eval_data.evaluation_results,
    }

    saved_files = {}

    # Export each sheet to CSV
    for sheet_key, df in editor_map.items():
        output_path = os.path.join(base_dir, f"{sheet_key}.csv")
        df.to_csv(output_path, index=False)
        if sheet_key in sheet_names:  # Only use sheet_names mapping for sheets in the schema
            saved_files[sheet_names[sheet_key]] = output_path
        else:
            saved_files[sheet_key] = output_path

    return saved_files


if __name__ == "__main__":
    saved_files = save_sheets_as_csv()

    print("\nSaved the following files:")
    for sheet_name, file_path in saved_files.items():
        print(f"{sheet_name}: {file_path}")
