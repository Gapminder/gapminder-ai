import argparse
import json
import os
from enum import Enum

import polars as pl

from lib.app_singleton import AppSingleton


class JsonlFormat(Enum):
    OPENAI = "openai"
    VERTEX = "vertex"
    MISTRAL = "mistral"


logger = AppSingleton().get_logger()


def ensure_complete_options(question_options: pl.DataFrame) -> pl.DataFrame:
    """
    Ensure each question has exactly A, B, and C options.
    If any options are missing, create empty options with the correct letter.

    Args:
        question_options: DataFrame with columns [question_option_id, question_id,
                        language, letter, question_option, correctness_of_answer_option]

    Returns:
        DataFrame with complete A, B, C options for each question
    """
    # First fill in missing letters for existing rows
    # Get the count of options per question/language
    option_counts = question_options.group_by(["question_id", "language"]).agg(pl.count().alias("count"))

    # Join back to original data
    question_options = question_options.join(option_counts, on=["question_id", "language"], how="left")

    # Fill missing letters based on row number within each group
    question_options = question_options.with_columns(
        pl.when(pl.col("letter").is_null())
        .then(pl.col("count").rank("ordinal").cast(pl.Utf8).replace({"1": "A", "2": "B", "3": "C"}))
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
    complete_options = required_options.join(question_options, on=["question_id", "language", "letter"], how="left")

    # Fill null values in question_option with empty string
    return complete_options.with_columns(pl.col("question_option").fill_null(""))


def combine_questions_with_options(questions: pl.DataFrame, question_options: pl.DataFrame) -> pl.DataFrame:
    """
    Combine questions with their options to create a dataframe with:
    question_id, published_version_of_question, option_a, option_b, option_c

    Args:
        questions: DataFrame with columns [question_id, language, published_version_of_question]
        question_options: DataFrame with columns [question_option_id, question_id, language,
                        letter, question_option, correctness_of_answer_option]

    Returns:
        DataFrame with combined question and option data
    """
    # Ensure each question has A, B, C options
    question_options = ensure_complete_options(question_options)

    # Pivot question options to have one row per question with A, B, C options
    options_pivot = question_options.pivot(  # type: ignore
        values="question_option",
        index=["question_id", "language"],
        columns="letter",
        aggregate_function="first",
    )

    # Join with questions dataframe
    combined = questions.join(options_pivot, on=["question_id", "language"], how="inner")

    # Rename columns to option_a, option_b, option_c
    combined = combined.rename(
        {
            "A": "option_a",
            "B": "option_b",
            "C": "option_c",
            "published_version_of_question": "question_text",
        }
    )

    # Select and order final columns
    return combined.select(["question_id", "question_text", "option_a", "option_b", "option_c"])


def generate_question_prompt_combinations(questions: pl.DataFrame, prompt_variations: pl.DataFrame) -> pl.DataFrame:
    """
    Generate all combinations of questions and prompt variations.

    Args:
        questions: DataFrame with columns [question_id, question_text, option_a, option_b, option_c]
        prompt_variations: DataFrame with columns [variation_id, question_template, question_prompt_template]

    Returns:
        DataFrame with columns [question_prompt_id, question_prompt_text]
    """
    # Create all combinations using cross join
    combinations = questions.join(prompt_variations, how="cross")

    # Convert to dictionaries for simpler string formatting
    combinations_dicts = combinations.to_dicts()

    # Process each combination
    processed = []
    for combo in combinations_dicts:
        # First format step: format question_template with question text and options
        formatted_question = combo["question_template"].format(
            question_text=combo["question_text"],
            option_a=combo["option_a"],
            option_b=combo["option_b"],
            option_c=combo["option_c"],
        )

        # Second format step: format question_prompt_template with formatted_question
        question_prompt_text = combo["question_prompt_template"].format(question=formatted_question)

        # Create the prompt ID and text
        question_prompt_id = f"{combo['question_id']}-{combo['variation_id']}"
        processed.append(
            {
                "prompt_id": question_prompt_id,
                "prompt_text": question_prompt_text,
            }
        )

    # Create final DataFrame and return
    return pl.DataFrame(processed)


def convert_to_jsonl_openai(
    df: pl.DataFrame,
    output_path: str,
    model: str,
    model_parameters: dict,
    id_prefix: str = "",
) -> None:
    """
    Convert a DataFrame of prompts to OpenAI JSONL format for batch processing.

    Args:
        df: DataFrame with columns [question_prompt_id, question_prompt_text]
        output_path: Path to save JSONL file
        model: OpenAI model to use
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for row in df.iter_rows(named=True):
            request_body = {
                "model": model,
                "messages": [
                    {"role": "user", "content": row["prompt_text"]},
                ],
                **model_parameters,
            }

            request_obj = {
                "custom_id": f"{id_prefix}{row['prompt_id']}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": request_body,
            }

            # Use json.dumps to ensure proper JSON formatting and UTF-8 encoding
            json_line = json.dumps(request_obj, ensure_ascii=False)
            f.write(f"{json_line}\n")


def convert_to_jsonl_mistral(
    df: pl.DataFrame,
    output_path: str,
    model_parameters: dict,
    id_prefix: str = "",
) -> None:
    """
    Convert a DataFrame of prompts to Mistral JSONL format for batch processing.

    Args:
        df: DataFrame with columns [question_prompt_id, question_prompt_text]
        output_path: Path to save JSONL file
        model_parameters: Parameters for the model
        id_prefix: Prefix to add to custom_id
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for row in df.iter_rows(named=True):
            # Create the body with messages and parameters
            body = {
                "messages": [
                    {"role": "user", "content": row["prompt_text"]},
                ],
                **model_parameters,
            }

            # Create the request object
            request_obj = {
                "custom_id": f"{id_prefix}{row['prompt_id']}",
                "body": body,
            }

            # Use json.dumps to ensure proper JSON formatting and UTF-8 encoding
            json_line = json.dumps(request_obj, ensure_ascii=False)
            f.write(f"{json_line}\n")


def convert_to_jsonl_vertex(df: pl.DataFrame, output_path: str, model_parameters: dict) -> None:
    """
    Convert a DataFrame of prompts to Vertex AI JSONL format for batch processing.

    Args:
        df: DataFrame with columns [question_prompt_id, question_prompt_text]
        output_path: Path to save JSONL file
        temperature: Temperature setting for generation
        id_prefix: Prefix to add to custom_id
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for row in df.iter_rows(named=True):
            request_obj = {
                "request": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": row["prompt_text"]}],
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

            # Use json.dumps to ensure proper JSON formatting and UTF-8 encoding
            json_line = json.dumps(request_obj, ensure_ascii=False)
            f.write(f"{json_line}\n")


def main(base_path, model_config_id, jsonl_format):
    # Construct input paths
    sheets_dir = os.path.join(base_path, "ai_eval_sheets")
    questions_path = os.path.join(sheets_dir, "questions.csv")
    question_options_path = os.path.join(sheets_dir, "question_options.csv")
    prompt_variations_path = os.path.join(sheets_dir, "prompt_variations.csv")
    model_configurations_path = os.path.join(sheets_dir, "gen_ai_model_configs.csv")

    # Read input files
    questions = pl.read_csv(questions_path)
    question_options = pl.read_csv(question_options_path)
    prompt_template_variations = pl.read_csv(prompt_variations_path)
    model_configurations = pl.read_csv(model_configurations_path)

    # Print experiment size information
    print(f"Number of questions: {questions.height}")
    print(f"Number of prompt templates: {prompt_template_variations.height}")
    print(f"Total combinations: {questions.height * prompt_template_variations.height}")

    # Combine questions with options
    combined_questions = combine_questions_with_options(questions, question_options)

    # Generate question-prompt combinations
    question_prompts = generate_question_prompt_combinations(combined_questions, prompt_template_variations)

    # Find and validate model configuration
    model_config = model_configurations.filter(pl.col("model_config_id") == model_config_id)

    if model_config.height == 0:
        raise ValueError(f"Model config ID {model_config_id} not found")

    # Get model parameters
    model_id = model_config["model_id"][0]
    if model_id.startswith("anthropic/"):
        model_id = model_id.replace("anthropic/", "")
    model_parameters = model_config["model_parameters"][0]

    # parse the parameters
    if model_parameters is not None:
        try:
            params = json.loads(model_parameters)
            print(params)
        except json.JSONDecodeError:
            logger.warning(f"Could not parse model_parameters: {model_parameters}")
            params = {}

    # Save as JSONL file in selected format with model config prefix
    jsonl_output_path = os.path.join(base_path, f"{model_config_id}-question_prompts.jsonl")

    # Only save prompt mapping CSV for Vertex format
    if JsonlFormat(jsonl_format) == JsonlFormat.VERTEX:
        csv_output_path = os.path.join(
            base_path,
            f"{model_config_id}-question_prompts-prompt-mapping.csv",
        )
        question_prompts.write_csv(csv_output_path)
        print(f"Saved prompt mapping to {csv_output_path}")

    # Convert to appropriate JSONL format
    if JsonlFormat(jsonl_format) == JsonlFormat.OPENAI:
        convert_to_jsonl_openai(
            question_prompts,
            jsonl_output_path,
            model=model_id,
            model_parameters=params,
            id_prefix=f"{model_config_id}-",  # Use model_config_id as prefix
        )
    elif JsonlFormat(jsonl_format) == JsonlFormat.MISTRAL:
        convert_to_jsonl_mistral(
            question_prompts,
            jsonl_output_path,
            model_parameters=params,
            id_prefix=f"{model_config_id}-",  # Use model_config_id as prefix
        )
    else:  # Vertex format
        convert_to_jsonl_vertex(
            question_prompts,
            jsonl_output_path,
            model_parameters=params,
        )

    print(f"Saved {len(question_prompts)} prompts to {jsonl_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate question prompts")
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory containing ai_eval_sheets folder",
    )
    parser.add_argument(
        "--model-config-id",
        type=str,
        required=True,
        help="ID of the model configuration to use",
    )
    parser.add_argument(
        "--jsonl-format",
        type=str,
        choices=[f.value for f in JsonlFormat],
        default=JsonlFormat.OPENAI.value,
        help="Format of JSONL output (openai, vertex, or mistral)",
    )
    args = parser.parse_args()

    main(args.base_path, args.model_config_id, args.jsonl_format)
