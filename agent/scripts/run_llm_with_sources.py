"""
Script to create a system prompt from markdown files in agent/sources
and send a question to Vertex AI's Gemini 1.5 Pro model using native SDK.
Includes native Vertex AI caching support.
"""

import os
import glob
import vertexai
import datetime
from google.oauth2 import service_account
from vertexai.preview.caching import CachedContent  # type: ignore
from vertexai.generative_models import GenerativeModel, Part


# Hardcoded question to ask the LLM
USER_QUESTION = """In 2022, the UN spent around $6.4 billion to help refugees worldwide.
How much did Western European governments spend to help refugees within their countries?

A. Less than $3 billion
B. Around $5 billion
C. More than $20 billion
"""

# Configuration - these should ideally be configurable or taken from environment
MODEL_ID = "gemini-2.0-flash-001"
CACHE_NAME = "gapminder_llm_cache_v1"
PROJECT_ID = "gapminder-ai"
LOCATION = "us-central1"  # Default location for Gemini models


def load_system_prompt(directory, max_files=3):
    """
    Load markdown files from the specified directory and concatenate their contents
    to create a system prompt.

    Args:
        directory (str): Path to the directory containing markdown files
        max_files (int): Maximum number of files to include (default: 10)

    Returns:
        str: Concatenated content of markdown files with instructions
    """
    # Find all markdown files in the directory
    md_files = glob.glob(os.path.join(directory, "*.md"))

    if not md_files:
        raise FileNotFoundError(f"No markdown files found in {directory}")

    # Limit to max_files
    md_files = md_files[:max_files]

    # Print the file names for reference
    print("\nFiles being used for the system prompt:")
    for i, file_path in enumerate(md_files, 1):
        print(f"{i}. {os.path.basename(file_path)}")
    print()

    # Create system instruction part
    system_instruction = Part.from_text(
        """You are an assistant that answers questions based ONLY on the information
provided in the following documents.
If the answer cannot be found in the documents, say "I don't have enough
information to answer this question based on the provided documents."
Do not use any prior knowledge beyond what is contained in these documents.
"""
    )

    # Create document parts
    document_parts = []
    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                document_parts.append(Part.from_text(f"Document: {os.path.basename(file_path)}\n{content}"))
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    return system_instruction, document_parts


if __name__ == "__main__":
    # setup vertex AI env with service account credentials
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.abspath(os.path.join(script_dir, "..", "service-account.json"))
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

    # Get the absolute path to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set the path to the sources directory (relative to the script location)
    sources_dir = os.path.abspath(os.path.join(script_dir, "..", "sources"))

    print(f"Loading markdown files from: {sources_dir}")

    try:
        # Load the system instruction and document parts
        system_instruction, document_parts = load_system_prompt(sources_dir)

        # Try to find existing cache by display name
        caches = list(CachedContent.list())
        cache = next((c for c in caches if c.display_name == CACHE_NAME), None)

        if cache:
            print(f"Using existing cache: {cache.display_name} (ID: {cache.name})")
        else:
            print(f"Creating new cache: {CACHE_NAME}")
            cache = CachedContent.create(
                model_name=f"publishers/google/models/{MODEL_ID}",
                display_name=CACHE_NAME,
                system_instruction=system_instruction,
                contents=document_parts,  # Cache the document parts
                ttl=datetime.timedelta(minutes=5),
            )

        print("Sending request to Vertex AI with caching...")

        # Prepare the Vertex AI Gemini model with system instruction
        model = GenerativeModel(MODEL_ID).from_cached_content(cache.name)

        # Make the request with caching enabled
        response = model.generate_content(
            contents=[USER_QUESTION],
            generation_config={"temperature": 0.0, "max_output_tokens": 2048},
        )

        # Print the response
        print("\n--- LLM Response ---\n")
        print(response.text)

        # Print token usage and cache information
        print("\n--- Usage Metadata ---")
        if response.usage_metadata:
            print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
            print(f"Candidates tokens: {response.usage_metadata.candidates_token_count}")
            print(f"Total tokens: {response.usage_metadata.total_token_count}")

            # Cache stats
            if response.usage_metadata.cached_content_token_count > 0:
                print(f"\nCache hit! (Saved {response.usage_metadata.cached_content_token_count} tokens)")
                print(f"Cache name: {cache.name}")
            else:
                print("\nNo cache hit - response was generated fresh.")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Full error details: {repr(e)}")
