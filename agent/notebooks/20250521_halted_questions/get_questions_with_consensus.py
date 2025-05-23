import polars as pl
import os
from pathlib import Path

# Load the consensus results
consensus_results = pl.read_csv("model_consensus_results.csv")

# Filter for questions with perfect agreement (100%)
perfect_agreement = consensus_results.filter(pl.col("consensus_percentage") == 100.0)

# Sort by most_common_result to group similar answers
perfect_agreement = perfect_agreement.sort("most_common_result")

# Get count by result type
result_counts = perfect_agreement.group_by("most_common_result").agg(
    pl.len().alias("count")
).sort("count", descending=True)

print("Questions with 100% agreement across all models:")
print(result_counts)

print("\nBreakdown of questions with perfect agreement:")

# Load the questions file with the original question text
questions_path = "ai_eval_sheets/questions.csv"
if os.path.exists(questions_path):
    questions_df = pl.read_csv(questions_path)
    print(f"\nLoaded questions file with {questions_df.height} questions")

    # Print some debug info about the question IDs in both files
    print("\nQuestion IDs in questions.csv:")
    question_ids_in_file = questions_df.select("question_id").to_series().to_list()
    print(f"First 5 question IDs: {question_ids_in_file[:5]}")
    print(f"Types: {[type(qid) for qid in question_ids_in_file[:5]]}")

    print("\nQuestion IDs in model_consensus_results.csv:")
    consensus_ids = consensus_results.select("question").to_series().to_list()
    print(f"First 5 question IDs: {consensus_ids[:5]}")
    print(f"Types: {[type(qid) for qid in consensus_ids[:5]]}")

    # Create a mapping from question ID to question text
    question_map = {}
    for row in questions_df.to_dicts():
        # Store the mapping with both string and integer keys to ensure matching
        q_id = row["question_id"]
        q_text = row["published_version_of_question"]
        question_map[str(q_id)] = q_text
        if isinstance(q_id, int) or str(q_id).isdigit():
            question_map[int(q_id)] = q_text

    print(f"Successfully mapped {len(question_map)} questions")

    # Display questions with perfect agreement
    for result_type in ["correct", "wrong", "very_wrong"]:
        questions = perfect_agreement.filter(pl.col("most_common_result") == result_type)

        print(f"\n{questions.height} questions where all models agreed on '{result_type}':")

        for row in questions.to_dicts():
            q_id = row["question"]
            # Attempt different formats of the question ID (e.g., with/without string conversion)
            if q_id in question_map:
                print(f"  Q{q_id}: {question_map[q_id]}")
            elif str(q_id) in question_map:
                print(f"  Q{q_id}: {question_map[str(q_id)]}")
            else:
                print(f"  Q{q_id}: [Question text not found]")

else:
    print("Questions file not found. Displaying question IDs only.")

    # Group by result type and list question IDs
    for result_type in ["correct", "wrong", "very_wrong"]:
        questions = perfect_agreement.filter(pl.col("most_common_result") == result_type)

        print(f"\n{questions.height} questions where all models agreed on '{result_type}':")
        question_ids = questions.get_column("question").to_list()
        print(f"  Question IDs: {question_ids}")

# Print strong agreement (80-99%) statistics
strong_agreement = consensus_results.filter(
    (pl.col("consensus_percentage") >= 80.0) &
    (pl.col("consensus_percentage") < 100.0)
)

print("\nQuestions with strong agreement (80-99%):")
strong_result_counts = strong_agreement.group_by("most_common_result").agg(
    pl.len().alias("count")
).sort("count", descending=True)

print(strong_result_counts)

# Summarize findings
print("\nSUMMARY OF MODEL CONSENSUS:")
print(f"- {perfect_agreement.height} questions with 100% agreement (all 5 models gave the same answer)")
print(f"- {strong_agreement.height} questions with 80-99% agreement (4 out of 5 models agreed)")

print("\nRegardless of correctness, this analysis shows which questions tend to produce")
print("consistent answers across different model configurations.")
