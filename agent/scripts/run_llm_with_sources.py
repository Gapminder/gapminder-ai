#!/usr/bin/env python3
"""
Script to create a system prompt from markdown files in agent/sources
and send a question to Vertex AI's Gemini 1.5 Pro model using LiteLLM.
"""

import os
import glob
import litellm
import json

# Hardcoded question to ask the LLM
USER_QUESTION = "What is the main theme across these documents?"

## GET CREDENTIALS
## RUN ##
# !gcloud auth application-default login - run this to add vertex credentials to your env
## OR ##
file_path = "service-account.json"  # FIXME: use relative path from script folder.

# Load the JSON file
with open(file_path, "r") as file:
    vertex_credentials = json.load(file)

# Convert to JSON string
vertex_credentials_json = json.dumps(vertex_credentials)


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

    # Start with instructions for the model
    system_prompt = """You are an assistant that answers questions based ONLY on the information
provided in the following documents.
If the answer cannot be found in the documents, say "I don't have enough
information to answer this question based on the provided documents."
Do not use any prior knowledge beyond what is contained in these documents.
Here are the documents:

"""

    # Read and concatenate the content of each file
    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Add a separator between files for clarity
                system_prompt += f"\n\n--- Document: {os.path.basename(file_path)} ---\n\n"
                system_prompt += content
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    return system_prompt


if __name__ == "__main__":
    # IMPORTANT: Ensure Google Cloud authentication is set up
    # Either set GOOGLE_APPLICATION_CREDENTIALS environment variable
    # or use Application Default Credentials

    # Get the absolute path to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set the path to the sources directory (relative to the script location)
    sources_dir = os.path.abspath(os.path.join(script_dir, "..", "sources"))

    print(f"Loading markdown files from: {sources_dir}")

    try:
        # Load the system prompt content
        system_prompt_content = load_system_prompt(sources_dir)

        print(f"Loaded system prompt with {len(system_prompt_content)} characters")

        # Prepare the messages for the LLM
        messages = [  # noqa
            {"role": "system", "content": system_prompt_content},
            {"role": "user", "content": USER_QUESTION},
        ]

        print("Sending request to Vertex AI Gemini 1.5 Pro...")

        # Call the LLM with caching enabled
        response = litellm.completion(
            model="vertex_ai/gemini-1.5-pro-002",
            messages=messages,
            caching="vertex_ai",  # Enable Vertex AI's native caching
            # ttl="300s",
            vertex_credentials=vertex_credentials_json,
        )

        # Print the entire response object
        print("\n--- Full Response Object ---\n")
        print(f"Response type: {type(response)}")
        print(f"Response dir: {dir(response)}")
        print("\nResponse representation:")
        print(repr(response))

        # Extract and print just the response content
        assistant_message = response.choices[0].message.content
        print("\n--- LLM Response Content ---\n")
        print(assistant_message)

        # Print token usage information
        print("\n--- Token Usage ---")
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            print(f"Usage object: {usage}")
            print(f"Usage dir: {dir(usage)}")
            print(f"Input tokens: {usage.prompt_tokens}")
            print(f"Output tokens: {usage.completion_tokens}")
            print(f"Total tokens: {usage.total_tokens}")

            # Check if there's cached token information
            if hasattr(usage, "cached_prompt_tokens"):
                print(f"Cached input tokens: {usage.cached_prompt_tokens}")
            elif hasattr(response, "_cached") and response._cached:
                print("Response was cached")
                print(f"Cache info: {response._cached}")
            else:
                print("No cache information available")

            # Check for any other cache-related attributes
            for attr in dir(response):
                if "cache" in attr.lower():
                    print(f"Cache-related attribute '{attr}': {getattr(response, attr)}")
        else:
            print("Token usage information not available in the response")

        # Check for any litellm specific attributes
        print("\n--- LiteLLM Specific Information ---")
        litellm_attrs = ["_response_ms", "_cached", "id", "model", "created"]
        for attr in litellm_attrs:
            if hasattr(response, attr):
                print(f"{attr}: {getattr(response, attr)}")

    except Exception as e:
        print(f"Error: {e}")
