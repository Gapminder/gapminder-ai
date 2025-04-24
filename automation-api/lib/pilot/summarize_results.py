"""
Automate processing of experiment results from JSONL files to Parquet summaries.
"""

import argparse
import json
import logging
import re
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import polars as pl

logger = logging.getLogger(__name__)

# Global dictionary to cache evaluator prefixes loaded from CSV
_evaluator_prefixes: Optional[Dict[str, str]] = None


def load_evaluator_prefixes(input_dir: Path) -> Dict[str, str]:
    """
    Load evaluator prefixes from the evaluators.csv file.

    Args:
        input_dir: Path to the experiment directory

    Returns:
        Dictionary mapping evaluator_id to metric_prefix
    """
    global _evaluator_prefixes

    # Return cached result if already loaded
    if _evaluator_prefixes is not None:
        return _evaluator_prefixes

    # Initialize empty dictionary
    _evaluator_prefixes = {}

    # Construct path to evaluators.csv
    evaluators_csv_path = input_dir / "ai_eval_sheets" / "evaluators.csv"

    # Check if file exists
    if not evaluators_csv_path.exists():
        logger.warning(
            f"Evaluators configuration not found at {evaluators_csv_path}. "
            "Will use default evaluator prefix mapping."
        )
        return _evaluator_prefixes

    try:
        # Read CSV file with polars
        df = pl.read_csv(evaluators_csv_path)

        # Check if required columns exist
        required_columns = ["evaluator_id", "metric_prefix"]
        if not all(col in df.columns for col in required_columns):
            logger.warning(
                f"Required columns {required_columns} not found in {evaluators_csv_path}. "
                "Will use default evaluator prefix mapping."
            )
            return _evaluator_prefixes

        # Extract mapping as dictionary
        for row in df.select(required_columns).iter_rows():
            evaluator_id, metric_prefix = row
            # Remove trailing underscore if present (will be added consistently later)
            prefix = metric_prefix.rstrip("_")
            _evaluator_prefixes[evaluator_id] = prefix

        logger.info(f"Loaded {len(_evaluator_prefixes)} evaluator prefixes from {evaluators_csv_path}")

    except Exception as e:
        logger.warning(
            f"Error loading evaluator prefixes from {evaluators_csv_path}: {str(e)}. "
            "Will use default evaluator prefix mapping."
        )

    return _evaluator_prefixes


def get_evaluator_prefix(evaluator_id: str, prefixes: Optional[Dict[str, str]] = None) -> str:
    """
    Map evaluator ID to column prefix, using configuration from evaluators.csv if available.
    Falls back to substring matching if the evaluator is not found in the configuration.

    Args:
        evaluator_id: ID of the evaluator
        prefixes: Dictionary of evaluator prefixes from load_evaluator_prefixes

    Returns:
        Column prefix to use for the evaluator
    """
    # If we have a mapping and the evaluator is in it, use that
    if prefixes and evaluator_id in prefixes:
        return prefixes[evaluator_id]

    # Fall back to substring matching
    evaluator_id = evaluator_id.lower()
    if "claude" in evaluator_id:
        return "claude"
    elif "gpt" in evaluator_id:
        return "gpt4"
    elif "gemini" in evaluator_id:
        return "gemini"
    elif "mistral" in evaluator_id:
        return "mistral"
    return evaluator_id.replace("-", "_")


# TODO: use information from evaluators.csv from ai eval sheet to
# find out if all evals are run
def find_file_groups(folder: Path) -> Dict[str, Tuple[Path, List[Path]]]:
    """Group response files with their corresponding eval files."""
    file_pattern = re.compile(
        r"(?P<model_id>.+?)-question_prompts-response" r"(-eval-prompts-(?P<evaluator_id>.+?)-response)?\.jsonl$"
    )

    groups: Dict[str, Tuple[Path, List[Path]]] = {}
    eval_files = []

    for path in folder.glob("*.jsonl"):
        match = file_pattern.match(path.name)
        if not match:
            continue

        model_id = match.group("model_id")
        if not match.group("evaluator_id"):
            groups[model_id] = (path, [])
        else:
            eval_files.append((model_id, path))

    # Attach eval files to their response groups
    for model_id, eval_path in eval_files:
        if model_id in groups:
            groups[model_id][1].append(eval_path)

    return groups


def load_jsonl(file_path: Path) -> List[Dict]:
    """Load a JSONL file into a list of dictionaries."""
    with file_path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def extract_custom_id_info(custom_id: str, expected_model_config_id: str) -> Dict[str, str]:
    """Extract info from custom_id and validate model_config_id matches expected"""
    parts = custom_id.split("-")
    excludes = ["question", "q", "eval"]
    parts = [x for x in parts if x not in excludes]

    # First part should be model_config_id
    model_config_id = parts[0]
    if model_config_id != expected_model_config_id:
        raise ValueError(
            f"Model config ID mismatch: expected {expected_model_config_id}, "
            f"got {model_config_id} in custom_id {custom_id}"
        )

    if len(parts) == 3:  # question responses
        return dict(zip(["model_config_id", "question_id", "prompt_variation_id"], parts))
    else:
        return dict(
            zip(
                ["model_config_id", "question_id", "prompt_variation_id", "metric_id"],
                parts,
            )
        )


# FIXME: this is a shortcut, we should get proper dict from the
# AI eval sheet configuration.
def extract_score(eval_text):
    """Extract A/B/C/D letter grade from eval text, returning score from 0-3."""
    mapping = {"A": 0, "B": 1, "C": 2, "D": 3}

    # Handle null or non-string responses
    if eval_text is None or not isinstance(eval_text, str):
        return -1

    try:
        # Get the last line
        last_line = eval_text.strip().split("\n")[-1]
        # Be defensive, get the last word of this line, make it uppercase
        grade = last_line.split(" ")[-1].upper()
        return mapping.get(grade, -1)  # Use get with default instead of try/except
    except Exception as e:
        logger.info(f"ERROR getting score: {str(e)}\nText: {str(eval_text)[:30]}...")
        return -1


def process_responses(responses: List[Dict], model_id: str) -> List[Dict]:
    """Process response records into structured data."""
    processed = []
    for resp in responses:
        info = extract_custom_id_info(resp["custom_id"], model_id)
        processed.append(
            {
                "model_config_id": info["model_config_id"],
                "question_id": info["question_id"],
                "prompt_variation_id": info["prompt_variation_id"],
                "response": resp.get("content", "NOT_ANSWERED"),
            }
        )
    return processed


def process_evals(evals: List[Dict], evaluator_prefix: str, model_id: str) -> List[Dict]:
    """Process evaluation records into structured scores."""
    processed = []
    for eval_rec in evals:
        info = extract_custom_id_info(eval_rec["custom_id"], model_id)
        processed.append(
            {
                "model_config_id": info["model_config_id"],
                "question_id": info["question_id"],
                "prompt_variation_id": info["prompt_variation_id"],
                "metric_id": info.get("metric_id", ""),
                f"{evaluator_prefix}_score": extract_score(eval_rec.get("content", "")),
            }
        )
    return processed


def pivot_eval_df(df: pl.DataFrame, evalulator_prefix: str) -> pl.DataFrame:
    """Pivot evaluation dataframe to have metric_id values as columns"""
    pivoted = df.pivot(
        values=f"{evalulator_prefix}_score",
        index=["model_config_id", "question_id", "prompt_variation_id"],
        on="metric_id",
        aggregate_function="first",
    )

    # Rename columns to include evaluator name
    new_columns = []
    for col in pivoted.columns:
        if col in ["model_config_id", "question_id", "prompt_variation_id"]:
            new_columns.append(col)
        else:
            new_columns.append(f"{evalulator_prefix}_{col}")

    return pivoted.rename(dict(zip(pivoted.columns, new_columns)))


def calculate_final_score(scores: List[int]) -> int:
    """Determine final score by majority vote.

    Rules:
    1. If all scores are -1, return -1
    2. Remove all -1 scores before next steps
    3. If there's a clear majority winner, return that winner
    4. Otherwise, return 0
    """
    # Remove all -1 scores
    filtered_scores = [score for score in scores if score != -1]

    # If no valid scores left(i.e all are -1), return -1
    if not filtered_scores:
        return -1

    # Count occurrences of each score
    score_counts: Dict[int, int] = {}
    for score in filtered_scores:
        score_counts[score] = score_counts.get(score, 0) + 1

    # Find the most common score and its count
    most_common_score = 0
    max_count = 0

    for score, count in score_counts.items():
        if count > max_count:
            max_count = count
            most_common_score = score

    # Check if this is a clear winner (no other score has the same count)
    is_clear_winner = sum(1 for count in score_counts.values() if count == max_count) == 1

    return most_common_score if is_clear_winner else 0


def process_group(
    response_path: Path, eval_paths: List[Path], output_dir: Path, evaluator_prefixes: Dict[str, str]
) -> None:
    """Process a group of response + eval files into final output."""
    model_id = response_path.name.split("-")[0]

    # Load and process data
    responses = load_jsonl(response_path)
    response_df = pl.DataFrame(process_responses(responses, model_id))

    # Process evaluations
    eval_dfs = []
    for eval_path in eval_paths:
        eval_file_match = re.match(
            r".+?-question_prompts-response-eval-prompts-(?P<evaluator_id>.+?)-response\.jsonl$",
            eval_path.name,
        )
        evaluator_id = eval_file_match.group("evaluator_id") if eval_file_match else "unknown"
        prefix = get_evaluator_prefix(evaluator_id, evaluator_prefixes)
        evals = load_jsonl(eval_path)
        eval_df = pl.DataFrame(process_evals(evals, prefix, model_id))
        eval_dfs.append(pivot_eval_df(eval_df, prefix))

    # Combine all data
    combined_df = response_df
    for df in eval_dfs:
        combined_df = combined_df.join(df, on=["model_config_id", "question_id", "prompt_variation_id"], how="left")

    # Fill null evaluation scores with -1
    # And fille null response with n/a
    # Identify evaluation columns by excluding the joining columns
    # and response column
    joining_columns = [
        "model_config_id",
        "question_id",
        "prompt_variation_id",
        "response",
    ]
    eval_columns = [col for col in combined_df.columns if col not in joining_columns]

    combined_df = combined_df.with_columns([pl.col(col).fill_null(-1) for col in eval_columns]).with_columns(
        pl.col("response").fill_null("NOT_ANSWERED")
    )

    # Add final correctness score
    score_cols = [c for c in combined_df.columns if c.endswith("_correctness")]
    combined_df = combined_df.with_columns(
        pl.struct(score_cols)
        .map_elements(lambda x: calculate_final_score(x.values()), return_dtype=pl.Int32)
        .alias("final_correctness")
    )

    # Write output
    output_path = output_dir / f"{model_id}_output.parquet"
    combined_df.write_parquet(output_path)
    logger.info(f"Processed {model_id} → {output_path}")


def create_master_output(input_dir: str, language: str = "en-US") -> pl.DataFrame:
    """Create a master output DataFrame from parquet files in a folder.

    Args:
        output_folder: Folder containing parquet files with results
        language: Language code to add to results (default: "en-US")

    Returns:
        DataFrame with standardized columns for upload
    """
    # Define mapping for correctness values
    result_map = {-1: "n/a", 0: "fail", 1: "very_wrong", 2: "wrong", 3: "correct"}

    # Read and combine all parquet files
    res_list = [pl.read_parquet(x) for x in glob(f"{input_dir}/*parquet")]

    # make sure the columns are in same order
    cols = ["model_config_id", "question_id", "prompt_variation_id", "response", "final_correctness"]
    res_list = [r.select(cols) for r in res_list]

    res = pl.concat(res_list)

    # Add metadata columns and map correctness
    res = res.with_columns(
        pl.lit(language).alias("language"),
        pl.lit(input_dir.split("/")[-1].split("_")[0]).alias("last_evaluation_datetime"),
        pl.col("final_correctness").replace_strict(result_map).alias("result"),
    )

    # Select and rename columns for upload with correct order
    return res.select(
        [
            pl.col("question_id"),
            pl.col("language"),
            pl.col("prompt_variation_id"),
            pl.col("model_config_id").alias("model_configuration_id"),
            pl.col("last_evaluation_datetime"),
            pl.col("result"),
        ]
    )


def main(input_dir: Path, output_dir: Optional[Path] = None) -> None:
    """Process experiment results from input_dir and save to output_dir."""
    output_dir = output_dir or input_dir
    output_dir.mkdir(exist_ok=True)

    # Load evaluator prefixes from configuration file
    evaluator_prefixes = load_evaluator_prefixes(input_dir)

    file_groups = find_file_groups(input_dir)
    for model_id, (resp_path, eval_paths) in file_groups.items():
        logger.info(f"Processing {model_id}...")
        process_group(resp_path, eval_paths, output_dir, evaluator_prefixes)

    # Combine all parquet to create a master output csv file
    # I need to provide the fullpath, because it is needed for
    # computing the evaluation date.
    master_output = create_master_output(str(input_dir.resolve()))

    # Extract the basename from output_dir for the filename suffix
    basename = output_dir.name

    # Create the output CSV filename with the basename as suffix
    csv_output_path = output_dir / f"master_output_{basename}.csv"

    # Write to CSV with the correct filename
    master_output.write_csv(csv_output_path)
    logger.info(f"Created master output file: {csv_output_path}")
    logger.info("now you can archive/remove all jsonl files.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Generate consolidated Parquet files from experiment JSONL results")
    parser.add_argument("input_dir", type=Path, help="Directory containing response/eval JSONL files")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: same as input)",
    )

    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
