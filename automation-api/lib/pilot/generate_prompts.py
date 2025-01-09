import polars as pl

from lib.app_singleton import AppSingleton

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
    option_counts = question_options.group_by(["question_id", "language"]).agg(
        pl.count().alias("count")
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

    # Fill null values in question_option with empty string
    return complete_options.with_columns(pl.col("question_option").fill_null(""))


def combine_questions_with_options(
    questions: pl.DataFrame, question_options: pl.DataFrame
) -> pl.DataFrame:
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
    options_pivot = question_options.pivot(
        values="question_option",
        index=["question_id", "language"],
        columns="letter",
        aggregate_function="first",
    )

    # Join with questions dataframe
    combined = questions.join(
        options_pivot, on=["question_id", "language"], how="inner"
    )

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
    return combined.select(
        ["question_id", "question_text", "option_a", "option_b", "option_c"]
    )


def generate_question_prompt_combinations(
    questions: pl.DataFrame, prompt_variations: pl.DataFrame
) -> pl.DataFrame:
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
        question_prompt_text = combo["question_prompt_template"].format(
            question=formatted_question
        )

        # Create ID and add to results
        question_prompt_id = f"question-{combo['question_id']}-{combo['variation_id']}"
        processed.append(
            {
                "question_prompt_id": question_prompt_id,
                "question_prompt_text": question_prompt_text,
            }
        )

    # Create final DataFrame and return
    return pl.DataFrame(processed)


if __name__ == "__main__":
    # Read input files
    questions = pl.read_csv("questions.csv")
    question_options = pl.read_csv("question_options.csv")
    prompt_template_variations = pl.read_csv("prompt_variations.csv")

    # Combine questions with options
    combined_questions = combine_questions_with_options(questions, question_options)

    # Generate question-prompt combinations
    question_prompts = generate_question_prompt_combinations(
        combined_questions, prompt_template_variations
    )

    print(question_prompts)
