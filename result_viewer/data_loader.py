import pandas as pd


def load_parquet_data(file_path):
    """Load the parquet file into a pandas DataFrame."""
    return pd.read_parquet(file_path)


def get_unique_values(df, column):
    """Get unique values for a specific column."""
    return sorted(df[column].unique())


def filter_data(df, model_config_id, question_id, prompt_variation_id):
    """Filter the DataFrame based on the provided criteria."""
    return df[
        (df["model_config_id"] == model_config_id)
        & (df["question_id"] == question_id)
        & (df["prompt_variation_id"] == prompt_variation_id)
    ]
