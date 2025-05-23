import polars as pl
import os
from pathlib import Path

"""
This script creates a summary of questions where different LLM models showed high consensus
in their answers, regardless of whether those answers were correct or not.
"""

# Load the consensus results and questions data
consensus_results = pl.read_csv("model_consensus_results.csv")
questions_df = pl.read_csv("ai_eval_sheets/questions.csv")

# Create a mapping from question ID to question text
question_map = {}
for row in questions_df.to_dicts():
    q_id = row["question_id"]
    q_text = row["published_version_of_question"]
    question_map[int(q_id)] = q_text

# Filter for questions with perfect agreement (100%)
perfect_agreement = consensus_results.filter(pl.col("consensus_percentage") == 100.0)

# Filter for questions with strong agreement (80-99%)
strong_agreement = consensus_results.filter(
    (pl.col("consensus_percentage") >= 80.0) &
    (pl.col("consensus_percentage") < 100.0)
)

# Create summary dataframes with question text
def add_question_text(df):
    """Add the question text to the dataframe"""
    question_texts = []
    for row in df.to_dicts():
        q_id = row["question"]
        if q_id in question_map:
            question_texts.append(question_map[q_id])
        else:
            question_texts.append("[Question text not found]")

    return df.with_columns(pl.Series(name="question_text", values=question_texts))

# Add question text to the dataframes
perfect_agreement_with_text = add_question_text(perfect_agreement)
strong_agreement_with_text = add_question_text(strong_agreement)

# Save results to CSV files
perfect_agreement_with_text.write_csv("complete_agreement_questions.csv")
strong_agreement_with_text.write_csv("strong_agreement_questions.csv")

# Create a combined summary file
summary_lines = [
    "# CONSENSUS ANALYSIS SUMMARY",
    "",
    f"## Perfect Agreement (100% - All {perfect_agreement.height} questions where all 5 models gave the same answer)",
    "",
]

# Group perfect agreement by result type
for result_type in ["correct", "wrong", "very_wrong"]:
    questions = perfect_agreement_with_text.filter(pl.col("most_common_result") == result_type)
    summary_lines.append(f"### {questions.height} questions where all models agreed on '{result_type}'")
    summary_lines.append("")

    for i, row in enumerate(questions.to_dicts()):
        summary_lines.append(f"{i+1}. Q{row['question']}: {row['question_text']}")

    summary_lines.append("")

# Add strong agreement section
summary_lines.extend([
    f"## Strong Agreement (80-99% - {strong_agreement.height} questions where 4 out of 5 models agreed)",
    "",
])

# Group strong agreement by result type
for result_type in ["correct", "wrong", "very_wrong"]:
    questions = strong_agreement_with_text.filter(pl.col("most_common_result") == result_type)
    summary_lines.append(f"### {questions.height} questions where most models agreed on '{result_type}'")
    summary_lines.append("")

    for i, row in enumerate(questions.to_dicts()):
        # Include consensus percentage
        percentage = row["consensus_percentage"]
        summary_lines.append(f"{i+1}. Q{row['question']} ({percentage:.1f}% agreement): {row['question_text']}")

    summary_lines.append("")

# Add insights section
correct_perfect = perfect_agreement_with_text.filter(pl.col("most_common_result") == "correct").height
wrong_perfect = perfect_agreement_with_text.filter(pl.col("most_common_result") == "wrong").height
very_wrong_perfect = perfect_agreement_with_text.filter(pl.col("most_common_result") == "very_wrong").height

correct_strong = strong_agreement_with_text.filter(pl.col("most_common_result") == "correct").height
wrong_strong = strong_agreement_with_text.filter(pl.col("most_common_result") == "wrong").height
very_wrong_strong = strong_agreement_with_text.filter(pl.col("most_common_result") == "very_wrong").height

summary_lines.extend([
    "## Key Insights",
    "",
    "### Distribution of Agreement Types",
    "",
    "| Agreement Level | Correct | Wrong | Very Wrong | Total |",
    "|----------------|---------|-------|------------|-------|",
    f"| Perfect (100%) | {correct_perfect} | {wrong_perfect} | {very_wrong_perfect} | {perfect_agreement.height} |",
    f"| Strong (80-99%) | {correct_strong} | {wrong_strong} | {very_wrong_strong} | {strong_agreement.height} |",
    f"| Total | {correct_perfect + correct_strong} | {wrong_perfect + wrong_strong} | {very_wrong_perfect + very_wrong_strong} | {perfect_agreement.height + strong_agreement.height} |",
    "",
    "### Analysis",
    "",
    "1. **Types of Questions with High Consensus**:",
    "   - Questions about global statistics (poverty rates, undernourishment)",
    "   - Climate-related questions (global warming, CO2 emissions)",
    "   - Economic indicators (unemployment, GDP composition)",
    "",
    "2. **Questions Where Models Consistently Get Wrong Answers**:",
    "   - Complex projections and forecasts",
    "   - Regional comparisons requiring specific contextual knowledge",
    "   - Questions with potentially outdated information in training data",
    "",
    "3. **Implications**:",
    "   - High consensus doesn't always mean correct answers",
    "   - Models tend to agree on certain topics, which could indicate similar training data or reasoning patterns",
    "   - When models universally give wrong answers, it may reveal systematic limitations",
])

# Write summary to file
with open("consensus_analysis_summary.md", "w") as f:
    f.write("\n".join(summary_lines))

print("Analysis complete! Summary files created:")
print("1. complete_agreement_questions.csv - All questions with 100% model agreement")
print("2. strong_agreement_questions.csv - All questions with 80-99% model agreement")
print("3. consensus_analysis_summary.md - Detailed summary with analysis")
