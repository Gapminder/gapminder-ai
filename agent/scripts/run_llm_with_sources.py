"""
Script to create a system prompt from markdown files in agent/sources
and send questions from a JSONL file to Vertex AI's Gemini model using native SDK.
Includes native Vertex AI caching support and saves responses to CSV.
"""

import os
import glob
import json
import csv
import random
import time
import vertexai
import datetime
from google.oauth2 import service_account
from vertexai.preview.caching import CachedContent  # type: ignore
from vertexai.generative_models import GenerativeModel, Part

# Configuration - these should ideally be configurable or taken from environment
MODEL_ID = "gemini-2.5-pro-preview-03-25"
CACHE_NAME = "gapminder_llm_cache_v6"
PROJECT_ID = "gapminder-ai"
LOCATION = "us-central1"

SYSTEM_PROMPT = """You are an assistant that answers fact questions.
When answering questions, perfer to use the info from provided documents.
But you can also use other sources.
"""

# set random seed
random.seed(1)


def load_system_prompt(directory, source_file_percentage=0.5, content_percentage=0.1, content_min_len=10):
    """
    Load markdown files from the specified directory and concatenate their contents
    to create a system prompt.

    Args:
        directory (str): Path to the directory containing markdown files
        source_file_percentage (float): Percentage of files to include (0.0-1.0)
        content_percentage (float): Percentage of content to keep from each file (0.0-1.0)
        content_min_len (int): Minimum number of lines to keep from each file

    Returns:
        tuple: (system_instruction, document_parts) where:
            system_instruction: The base system prompt
            document_parts: List of document content parts
    """
    # Find all markdown files in the directory
    md_files = glob.glob(os.path.join(directory, "*.md"))

    if not md_files:
        raise FileNotFoundError(f"No markdown files found in {directory}")

    # Randomly select percentage of files
    if source_file_percentage == 1:
        num_to_load = len(md_files)
    else:
        num_to_load = max(1, int(len(md_files) * source_file_percentage))
    md_files = random.sample(md_files, num_to_load)

    # Print the file names for reference
    print("\nFiles being used for the system prompt:")
    for i, file_path in enumerate(md_files, 1):
        print(f"{i}. {os.path.basename(file_path)}")
    print()

    # Create system instruction part
    system_instruction = Part.from_text(SYSTEM_PROMPT)

    # Create document parts
    document_parts = []
    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Remove table separator lines (lines with only +, - and | characters)
                # Remove table separator lines and split into lines
                lines = [line for line in content.splitlines() if not all(c in "+-|" for c in line.strip())]

                # Calculate how many lines to keep
                keep_lines = max(content_min_len, int(len(lines) * content_percentage))
                if keep_lines < len(lines):
                    truncated_content = "\n".join(lines[:keep_lines])
                    truncated_content = f"{truncated_content}\n...[truncated]"
                else:
                    truncated_content = "\n".join(lines)

                document_parts.append(Part.from_text(f"Document: {os.path.basename(file_path)}\n{truncated_content}"))
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    return system_instruction, document_parts


if __name__ == "__main__":
    # Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    questions_file = os.path.abspath(os.path.join(script_dir, "question_prompts.jsonl"))
    output_dir = os.path.abspath(os.path.join(script_dir, "..", "output"))
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.abspath(os.path.join(output_dir, "responses.csv"))
    sources_dir = os.path.abspath(os.path.join(script_dir, "..", "sources"))

    # Setup vertex AI env with service account credentials
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.abspath(os.path.join(script_dir, "..", "service-account.json"))
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

    print(f"Loading markdown files from: {sources_dir}")
    print(f"Reading questions from: {questions_file}")
    print(f"Writing responses to: {output_csv}")

    try:
        # Load the system instruction and document parts
        system_instruction, document_parts = load_system_prompt(sources_dir, 1, 0.2, 30)

        # Read questions from JSONL file
        with open(questions_file, "r") as f:
            questions = [json.loads(line) for line in f]

        # Prepare results list
        results = []

        # Setup cache
        caches = list(CachedContent.list())
        cache = next((c for c in caches if c.display_name == CACHE_NAME), None)

        if not cache:
            cache = CachedContent.create(
                model_name=f"publishers/google/models/{MODEL_ID}",
                display_name=CACHE_NAME,
                system_instruction=system_instruction,
                contents=document_parts,
                ttl=datetime.timedelta(minutes=10),
            )

        model = GenerativeModel(MODEL_ID).from_cached_content(cache.name)

        # Process each question
        for i, question_data in enumerate(questions, 1):
            question_text = question_data["body"]["messages"][0]["content"]
            print(f"\nProcessing question {i}/{len(questions)}")
            print(question_text)
            print()

            max_retries = 3
            retry_delay = 1  # seconds
            for attempt in range(max_retries):
                try:
                    response = model.generate_content(
                        contents=[question_text],
                        generation_config={"temperature": 0.0, "max_output_tokens": 2048},
                    )

                    if not response.text:
                        if attempt < max_retries - 1:
                            print("Empty response, retrying...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print("Max retries reached for empty response")
                            response.text = "ERROR: Empty response after retries"

                    results.append({"question": question_text, "response": response.text})

                    print(f"Response received ({len(response.text)} chars)")
                    print(response.text)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"Error processing question {i}: {str(e)} - retrying...")
                        time.sleep(retry_delay)
                    else:
                        print(f"Max retries reached for question {i}: {str(e)}")
                        results.append({"question": question_text, "response": f"ERROR: {str(e)} after retries"})

        # Write results to CSV
        with open(output_csv, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["question", "response"])
            writer.writeheader()
            writer.writerows(results)

        print(f"\nSuccessfully processed {len(results)} questions")
        print(f"Responses saved to: {output_csv}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Full error details: {repr(e)}")
