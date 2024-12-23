import os
from datetime import datetime
from typing import Dict

from lib.ai_eval_spreadsheet.wrapper import (
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
    sheet_names,
)
from lib.config import read_config
from lib.gdrive.auth import AuthorizedClients


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

    # Load configuration
    config = read_config()
    spreadsheet_id = config["AI_EVAL_SPREADSHEET_ID"]

    # Initialize Google Sheets client
    authorized_clients = AuthorizedClients()
    spreadsheet = get_ai_eval_spreadsheet(authorized_clients, spreadsheet_id)

    # Read all data using existing wrapper
    ai_eval_data = read_ai_eval_data(spreadsheet)

    # Map of editors to their corresponding sheet names
    editor_map = {
        "questions": ai_eval_data.questions,
        "question_options": ai_eval_data.question_options,
        "prompt_variations": ai_eval_data.prompt_variations,
        "gen_ai_models": ai_eval_data.gen_ai_models,
        "gen_ai_model_configs": ai_eval_data.gen_ai_model_configs,
        "metrics": ai_eval_data.metrics,
        "evaluation_results": ai_eval_data.evaluation_results,
    }

    saved_files = {}

    # Export each sheet to CSV
    for sheet_key, editor in editor_map.items():
        df = editor.data.df
        output_path = os.path.join(base_dir, f"{sheet_key}.csv")
        df.to_csv(output_path, index=False)
        saved_files[sheet_names[sheet_key]] = output_path

    return saved_files


if __name__ == "__main__":
    saved_files = save_sheets_as_csv()

    print("\nSaved the following files:")
    for sheet_name, file_path in saved_files.items():
        print(f"{sheet_name}: {file_path}")
