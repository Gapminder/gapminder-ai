# Parquet Data Comparison Tool

A simple interface to compare data in parquet files side by side with different filters.

## Features

- Side-by-side comparison of model responses
- Filtering by model_config_id, question_id, and prompt_variation_id
- Display of correctness metrics (GPT-4, Claude, Gemini, Final)
- Navigation between questions

## Installation

1. Clone this repository
2. Install the required packages:
  ```
    pip install -r requirements.txt
  ```


## Usage

1. Run the Streamlit app:
  ```
    streamlit run app.py
  ```
2. Upload your parquet file through the interface
3. Use the filters to select which data to compare
4. Navigate between questions using the Previous/Next buttons

## Data Format

The tool expects a parquet file with the following columns:
- model_config_id
- question_id
- prompt_variation_id
- response
- gpt4_correctness
- claude_correctness
- gemini_correctness
- final_correctness

## Customization

You can modify the CSS in `styles/main.css` to change the appearance of the app.
