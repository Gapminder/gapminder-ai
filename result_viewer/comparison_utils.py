import difflib


def get_comparison_data(df, model_config_id1, model_config_id2, question_id, prompt_variation_id):
    """Get data for side-by-side comparison."""
    data1 = df[
        (df["model_config_id"] == model_config_id1)
        & (df["question_id"] == question_id)
        & (df["prompt_variation_id"] == prompt_variation_id)
    ]

    data2 = df[
        (df["model_config_id"] == model_config_id2)
        & (df["question_id"] == question_id)
        & (df["prompt_variation_id"] == prompt_variation_id)
    ]

    return data1, data2


def highlight_differences(text1, text2):
    """Highlight differences between two text responses.

    This function is not currently used in the main app but could be
    integrated for more advanced text comparison.
    """
    if not text1 or not text2:
        return text1, text2

    d = difflib.Differ()
    diff = list(d.compare(text1.splitlines(), text2.splitlines()))

    # Process the differences (simplified approach)
    highlighted1 = []
    highlighted2 = []

    for line in diff:
        if line.startswith("  "):  # unchanged
            highlighted1.append(line[2:])
            highlighted2.append(line[2:])
        elif line.startswith("- "):  # in text1 only
            highlighted1.append(f"**{line[2:]}**")
        elif line.startswith("+ "):  # in text2 only
            highlighted2.append(f"**{line[2:]}**")

    return "\n".join(highlighted1), "\n".join(highlighted2)
