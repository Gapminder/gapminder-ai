"""
Automate processing of experiment results from JSONL files to Parquet summaries.
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl

logger = logging.getLogger(__name__)


def get_evaluator_prefix(evaluator_id: str) -> str:
    """Map evaluator ID to column prefix using simple substring matching."""
    evaluator_id = evaluator_id.lower()
    if "claude" in evaluator_id:
        return "claude"
    elif "gpt" in evaluator_id:
        return "gpt"
    elif "gemini" in evaluator_id:
        return "gemini"
    return evaluator_id.replace("-", "_")


# TODO: use information from evaluators.csv from ai eval sheet to
# find out if all evals are run
def find_file_groups(folder: Path) -> Dict[str, Tuple[Path, List[Path]]]:
    """Group response files with their corresponding eval files."""
    file_pattern = re.compile(
        r"(?P<model_id>.+?)-question_prompts-response"
        r"(-eval-prompts-(?P<evaluator_id>.+?)-response)?\.jsonl$"
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


def extract_custom_id_info(custom_id: str, expected_model_id: str) -> Dict[str, str]:
    """Parse custom_id structure and validate model ID."""
    parts = [p for p in custom_id.split("-") if p not in {"question", "q", "eval"}]

    if parts[0] != expected_model_id:
        raise ValueError(f"Model ID mismatch in custom_id: {custom_id}")

    field_names = ["model_config_id", "question_id", "prompt_variation_id"]
    if len(parts) > 3:
        field_names.append("metric_id")

    return dict(zip(field_names, parts))


# FIXME: this is a shortcut, we should get proper dict from the
# AI eval sheet configuration.
def extract_score(eval_text: str) -> int:
    """Extract score from evaluation text (A=0, B=1, C=2, D=3)."""
    grade_map = {"A": 0, "B": 1, "C": 2, "D": 3}
    last_word = eval_text.strip().split()[-1].upper()
    return grade_map.get(last_word, -1)


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


def process_evals(
    evals: List[Dict], evaluator_prefix: str, model_id: str
) -> List[Dict]:
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


def pivot_eval_df(df: pl.DataFrame, evaluator_prefix: str) -> pl.DataFrame:
    """Pivot evaluation dataframe to metric-based columns."""
    return df.pivot(
        values=f"{evaluator_prefix}_score",
        index=["model_config_id", "question_id", "prompt_variation_id"],
        on="metric_id",
        aggregate_function="first",
    ).rename(lambda c: f"{evaluator_prefix}_{c}" if c != "metric_id" else c)


def calculate_final_score(scores: List[int]) -> int:
    """Determine final score by majority vote."""
    score_counts: Dict[int, int] = {}
    for score in scores:
        score_counts[score] = score_counts.get(score, 0) + 1

    max_count = max(score_counts.values(), default=0)
    return next((s for s, c in score_counts.items() if c == max_count), 0)


def process_group(
    response_path: Path, eval_paths: List[Path], output_dir: Path
) -> None:
    """Process a group of response + eval files into final output."""
    model_id = response_path.name.split("-")[0]

    # Load and process data
    responses = load_jsonl(response_path)
    response_df = pl.DataFrame(process_responses(responses, model_id))

    # Process evaluations
    eval_dfs = []
    for eval_path in eval_paths:
        evaluator_id = eval_path.stem.split("-")[-2]
        prefix = get_evaluator_prefix(evaluator_id)
        evals = load_jsonl(eval_path)
        eval_df = pl.DataFrame(process_evals(evals, prefix, model_id))
        eval_dfs.append(pivot_eval_df(eval_df, prefix))

    # Combine all data
    combined_df = response_df
    for df in eval_dfs:
        combined_df = combined_df.join(
            df, on=["model_config_id", "question_id", "prompt_variation_id"], how="left"
        )

    # Add final correctness score
    score_cols = [c for c in combined_df.columns if c.endswith("_correctness")]
    combined_df = combined_df.with_columns(
        pl.struct(score_cols)
        .map_elements(
            lambda x: calculate_final_score(x.values()), return_dtype=pl.Int32
        )
        .alias("final_correctness")
    )

    # Write output
    output_path = output_dir / f"{model_id}_output.parquet"
    combined_df.write_parquet(output_path)
    logger.info(f"Processed {model_id} → {output_path}")


def main():
    """Command line interface for processing experiment results."""
    parser = argparse.ArgumentParser(
        description="Generate consolidated Parquet files from experiment JSONL results"
    )
    parser.add_argument(
        "input_dir", type=Path, help="Directory containing response/eval JSONL files"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: same as input)",
    )

    args = parser.parse_args()
    output_dir = args.output_dir or args.input_dir
    output_dir.mkdir(exist_ok=True)

    file_groups = find_file_groups(args.input_dir)
    for model_id, (resp_path, eval_paths) in file_groups.items():
        logger.info(f"Processing {model_id}...")
        process_group(resp_path, eval_paths, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
