import polars as pl
import os
from pathlib import Path

# Set working directory to the datapoints folder
datapoints_dir = Path("datapoints")

# Read the rate files
correct_rate_df = pl.read_csv(datapoints_dir / "ddf--datapoints--correct_rate--by--question--model_configuration.csv")
wrong_rate_df = pl.read_csv(datapoints_dir / "ddf--datapoints--wrong_rate--by--question--model_configuration.csv")
very_wrong_rate_df = pl.read_csv(datapoints_dir / "ddf--datapoints--very_wrong_rate--by--question--model_configuration.csv")
indecisive_rate_df = pl.read_csv(datapoints_dir / "ddf--datapoints--indecisive_rate--by--question--model_configuration.csv")

# Join the dataframes
model_results = (
    correct_rate_df
    .join(wrong_rate_df, on=["question", "model_configuration"])
    .join(very_wrong_rate_df, on=["question", "model_configuration"])
    .join(indecisive_rate_df, on=["question", "model_configuration"])
)

# Determine the model result based on the highest rate
def determine_result(row):
    rates = {
        "correct": row["correct_rate"],
        "wrong": row["wrong_rate"],
        "very_wrong": row["very_wrong_rate"],
        "indecisive": row["indecisive_rate"]
    }

    # Find the result with the highest rate
    max_result = max(rates.items(), key=lambda x: x[1])
    result_type, max_rate = max_result

    # If the highest rate is greater than 85%, use that result
    # Otherwise, mark as "indecisive"
    threshold = 90.0
    if max_rate > threshold:
        return result_type
    else:
        return "indecisive"

# Apply the function to determine the model result for each row
results = []
for row in model_results.to_dicts():
    results.append({
        "question": row["question"],
        "model_configuration": row["model_configuration"],
        "evaluation_result": determine_result(row)
    })

# Convert to Polars DataFrame
model_results = pl.DataFrame(results)

# Get the distinct model configurations to count how many we have
model_configs = model_results.select("model_configuration").unique().sort("model_configuration")
num_models = len(model_configs)
print(f"Analyzing data from {num_models} model configurations: {model_configs.to_series().to_list()}")

# Pivot the data to have models as columns
model_consensus = (
    model_results.pivot(
        index="question",
        on="model_configuration",
        values="evaluation_result"
    )
)

# Function to check consensus
def check_consensus(row):
    # Get all the evaluation results excluding the question column
    results = [row[col] for col in row.keys() if col != "question"]

    # Count occurrences of each result
    result_counts = {}
    for result in results:
        if result in result_counts:
            result_counts[result] += 1
        else:
            result_counts[result] = 1

    # Find the most common result and its count
    most_common_result = None
    most_common_count = 0

    for result, count in result_counts.items():
        if count > most_common_count:
            most_common_result = result
            most_common_count = count

    # Calculate consensus percentage
    consensus_percentage = (most_common_count / len(results)) * 100

    return {
        "most_common_result": most_common_result,
        "consensus_count": most_common_count,
        "total_models": len(results),
        "consensus_percentage": consensus_percentage
    }

# Apply the consensus check to each row and create a new dataframe
consensus_results = []
for row in model_consensus.to_dicts():
    question = row["question"]
    consensus_info = check_consensus(row)
    consensus_results.append({
        "question": question,
        "most_common_result": consensus_info["most_common_result"],
        "consensus_count": consensus_info["consensus_count"],
        "total_models": consensus_info["total_models"],
        "consensus_percentage": consensus_info["consensus_percentage"]
    })

# Convert to Polars DataFrame and sort by consensus percentage
consensus_df = pl.DataFrame(consensus_results).sort("consensus_percentage", descending=True)

# Filter for high consensus (e.g., 80% or more)
high_consensus_threshold = 80  # 80% or higher consensus
high_consensus_df = consensus_df.filter(pl.col("consensus_percentage") >= high_consensus_threshold)

# Print results
print(f"\nQuestions with high consensus (≥{high_consensus_threshold}%):")
print(high_consensus_df)

# Save results to CSV
output_path = Path("model_consensus_results.csv")
consensus_df.write_csv(output_path)
print(f"\nFull results saved to {output_path}")

# Print some aggregate statistics
print("\nConsensus Distribution:")
consensus_ranges = [
    (100, "100% (Complete agreement)"),
    (80, "80-99% (Strong agreement)"),
    (60, "60-79% (Moderate agreement)"),
    (0, "Below 60% (Low agreement)")
]

for threshold, label in consensus_ranges:
    if threshold == 100:
        count = consensus_df.filter(pl.col("consensus_percentage") == 100).height
    elif threshold == 0:
        count = consensus_df.filter(pl.col("consensus_percentage") < 60).height
    else:
        upper = 100 if threshold == 80 else 80
        count = consensus_df.filter(
            (pl.col("consensus_percentage") >= threshold) &
            (pl.col("consensus_percentage") < upper)
        ).height

    percentage = (count / consensus_df.height) * 100
    print(f"{label}: {count} questions ({percentage:.1f}%)")

# Analyze agreement by result type
print("\nConsensus by Most Common Result:")
result_counts = consensus_df.group_by("most_common_result").agg(
    pl.count().alias("count"),
    pl.mean("consensus_percentage").alias("avg_consensus_percentage")
).sort("count", descending=True)

print(result_counts)

# For complete agreement questions, list the questions and their common result
complete_agreement = consensus_df.filter(pl.col("consensus_percentage") == 100)
if complete_agreement.height > 0:
    print("\nQuestions with 100% agreement across all models:")
    for row in complete_agreement.to_dicts():
        print(f"Question {row['question']}: All models responded '{row['most_common_result']}'")
