import argparse
import json
import logging
import os
from enum import Enum
from typing import Dict, List, Tuple

import polars as pl

from lib.app_singleton import AppSingleton


class JsonlFormat(Enum):
    OPENAI = "openai"
    VERTEX = "vertex"


logger = AppSingleton().get_logger()
logger.setLevel(logging.DEBUG)


def ensure_complete_options_with_correctness(
    question_options: pl.DataFrame,
) -> pl.DataFrame:
    """
    Ensure each question has exactly A, B, and C options with correctness values.
    If any options are missing, create empty options with the correct letter.

    Args:
        question_options: DataFrame with columns [question_option_id, question_id,
                        language, letter, question_option, correctness_of_answer_option]

    Returns:
        DataFrame with complete A, B, C options and correctness for each question
    """
    # First fill in missing letters for existing rows
    # Get the count of options per question/language
    option_counts = question_options.group_by(["question_id", "language"]).agg(
        pl.len().alias("count")
    )

    # Join back to original data
    question_options = question_options.join(
        option_counts, on=["question_id", "language"], how="left"
    )

    # Fill missing letters based on row number within each group
    question_options = question_options.with_columns(
        pl.when(pl.col("letter").is_null())
        .then(
            pl.col("count")
            .rank("ordinal")
            .cast(pl.Utf8)
            .replace({"1": "A", "2": "B", "3": "C"})
        )
        .otherwise(pl.col("letter"))
        .alias("letter")
    ).drop("count")

    # Now ensure we have all A, B, C options
    # Get all unique question_id and language combinations
    questions = question_options.select(["question_id", "language"]).unique()

    # Create a DataFrame with all required A, B, C options for each question
    required_options = questions.with_columns(
        [pl.concat_list([pl.lit("A"), pl.lit("B"), pl.lit("C")]).alias("letter")]
    ).explode("letter")

    # Join with existing options, filling missing ones with null values
    complete_options = required_options.join(
        question_options, on=["question_id", "language", "letter"], how="left"
    )

    # Map correctness values and fill nulls
    correctness_mapping = {"1": "Correct", "2": "Wrong", "3": "Very Wrong"}

    return complete_options.with_columns(
        [
            pl.col("question_option").fill_null(""),
            pl.col("correctness_of_answer_option").replace_strict(correctness_mapping),
        ]
    )


def combine_questions_with_options_and_correctness(
    questions: pl.DataFrame, question_options: pl.DataFrame
) -> pl.DataFrame:
    """
    Combine questions with their options and correctness values to create a dataframe.

    Args:
        questions: DataFrame with columns [question_id, language, published_version_of_question]
        question_options: DataFrame with columns [question_option_id, question_id, language,
                        letter, question_option, correctness_of_answer_option]

    Returns:
        DataFrame with combined question, option and correctness data
    """
    # Ensure each question has A, B, C options with correctness
    question_options = ensure_complete_options_with_correctness(question_options)

    # Pivot question options to have one row per question with A, B, C options
    options_pivot = question_options.pivot(
        values=["question_option", "correctness_of_answer_option"],
        index=["question_id", "language"],
        on="letter",
        aggregate_function="first",
    )

    # Rename the columns to be more descriptive
    column_mapping = {}
    for letter in ["A", "B", "C"]:
        column_mapping[f"question_option_{letter}"] = f"option_{letter.lower()}"
        column_mapping[
            f"correctness_of_answer_option_{letter}"
        ] = f"option_{letter.lower()}_correctness"

    # Join with questions dataframe and rename columns
    combined = questions.join(
        options_pivot, on=["question_id", "language"], how="inner"
    ).rename({"published_version_of_question": "question_text", **column_mapping})

    # Select and order final columns
    return combined.select(
        [
            "question_id",
            "question_text",
            "option_a",
            "option_a_correctness",
            "option_b",
            "option_b_correctness",
            "option_c",
            "option_c_correctness",
        ]
    )


def read_responses(response_file: str) -> Dict[str, str]:
    """
    Read response JSONL file and extract responses with their IDs.

    Args:
        response_file: Path to response JSONL file

    Returns:
        Dictionary mapping question_prompt_ids to response texts
    """
    responses = {}
    with open(response_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            content = data.get("content")
            if content is None:
                logger.debug(f"empty content: {line}")
                continue

            custom_id = data.get("custom_id", "")
            responses[custom_id] = content

    return responses


def generate_eval_prompts(
    questions_data: pl.DataFrame,
    responses: Dict[str, str],
    metrics: pl.DataFrame,
    output_path: str,
    model: str,
    model_parameters: dict,
    format: JsonlFormat,
) -> List[Tuple[str, str]]:
    """
    Generate evaluation prompts for each response and metric.

    Args:
        questions_data: DataFrame with question and option data
        responses: Dictionary of response texts keyed by question_prompt_id
        metrics: DataFrame with evaluation metric templates
        output_path: Path to save output JSONL file
        model: Model to use for evaluation
        model_parameters: parameters to the eval model
        format: json format to use
    """
    prompt_id_mapping = []

    with open(output_path, "w", encoding="utf-8") as f:
        for metric_row in metrics.iter_rows(named=True):
            prompt_template = metric_row["prompt"]
            metric_id = metric_row["name"]

            for question_row in questions_data.iter_rows(named=True):
                question_id = question_row["question_id"]

                # Get all responses for this question
                question_responses = {
                    prompt_id: text
                    for prompt_id, text in responses.items()
                    if f"-{question_id}-" in prompt_id
                }

                for prompt_id, response_text in question_responses.items():
                    # Format the evaluation prompt
                    eval_prompt = prompt_template.format(
                        raw_output=response_text,
                        question_text=question_row["question_text"],
                        option_a=question_row["option_a"],
                        option_a_correctness=question_row["option_a_correctness"],
                        option_b=question_row["option_b"],
                        option_b_correctness=question_row["option_b_correctness"],
                        option_c=question_row["option_c"],
                        option_c_correctness=question_row["option_c_correctness"],
                    )

                    # FIXME: anthropic expect custom id less than 64 chars.
                    # We should just update the generate_prompt.py to use shorter
                    # custom_id and no need to do it here.
                    custom_id = f"{prompt_id}-{metric_id}".replace("-question-", "-")
                    if len(custom_id) > 64:
                        raise ValueError("custom_id too long")
                    prompt_id_mapping.append((custom_id, eval_prompt))

                    if format == JsonlFormat.OPENAI:
                        # Create evaluation request object for OpenAI
                        eval_request = {
                            "model": model,
                            "messages": [{"role": "user", "content": eval_prompt}],
                            **model_parameters,
                        }

                        # Create the full request object with custom ID
                        request_obj = {
                            "custom_id": custom_id,
                            "method": "POST",
                            "url": "/v1/chat/completions",
                            "body": eval_request,
                        }
                    else:  # Vertex format
                        request_obj = {
                            "request": {
                                "contents": [
                                    {
                                        "role": "user",
                                        "parts": [{"text": eval_prompt}],
                                    }
                                ],
                                "generationConfig": model_parameters,
                                "safety_settings": [
                                    {
                                        "category": "HARM_CATEGORY_HARASSMENT",
                                        "threshold": "BLOCK_ONLY_HIGH",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_HATE_SPEECH",
                                        "threshold": "BLOCK_ONLY_HIGH",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                        "threshold": "BLOCK_ONLY_HIGH",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                        "threshold": "BLOCK_ONLY_HIGH",
                                    },
                                ],
                            }
                        }

                    # Write to output file
                    json_line = json.dumps(request_obj, ensure_ascii=False)
                    f.write(f"{json_line}\n")

    return prompt_id_mapping


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate evaluation prompts")
    parser.add_argument(
        "response-file",
        type=str,
        required=True,
        help="Path to response JSONL file",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    args = parser.parse_args()

    # Construct input paths
    sheets_dir = os.path.join(args.base_path, "ai_eval_sheets")
    questions_path = os.path.join(sheets_dir, "questions.csv")
    question_options_path = os.path.join(sheets_dir, "question_options.csv")
    metrics_path = os.path.join(sheets_dir, "metrics.csv")
    evaluators_path = os.path.join(sheets_dir, "evaluators.csv")

    # Read input files
    questions = pl.read_csv(questions_path)
    question_options = pl.read_csv(question_options_path)
    metrics = pl.read_csv(metrics_path)
    evaluators = pl.read_csv(evaluators_path)

    # Combine questions with options and correctness
    combined_questions = combine_questions_with_options_and_correctness(
        questions, question_options
    )

    # Read responses
    responses = read_responses(args.response_file)

    # Generate prompts for each evaluator
    for evaluator in evaluators.iter_rows(named=True):
        # Generate output path based on response file and evaluator
        response_basename = os.path.splitext(os.path.basename(args.response_file))[0]
        evaluator_id = evaluator["evaluator_id"].replace(".", "")
        output_path = os.path.join(
            args.base_path, f"{response_basename}-eval-prompts-{evaluator_id}.jsonl"
        )
        model_parameters = json.loads(evaluator["parameters"])

        # Generate evaluation prompts
        prompt_id_mapping = generate_eval_prompts(
            combined_questions,
            responses,
            metrics,
            output_path,
            model=evaluator["evaluator_id"],
            model_parameters=model_parameters,
            format=JsonlFormat(evaluator["jsonl_format"]),
        )

        print(
            f"Generated evaluation prompts for {evaluator['evaluator_id']} in {output_path}"
        )

        # Save prompt ID mapping if using Vertex format
        if evaluator["jsonl_format"] == JsonlFormat.VERTEX.value:
            mapping_df = pl.DataFrame(
                {
                    "prompt_id": [x[0] for x in prompt_id_mapping],
                    "prompt_text": [x[1] for x in prompt_id_mapping],
                }
            )
            mapping_path = output_path.replace(".jsonl", "-prompt-mapping.csv")
            mapping_df.write_csv(mapping_path)
            print(f"Generated prompt ID mapping in {mapping_path}")
