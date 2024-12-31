#!/bin/bash

# # Check if required environment variables are set
# if [ -z "$ANTHROPIC_API_KEY" ]; then
#     echo "Error: ANTHROPIC_API_KEY is not set"
#     exit 1
# fi

# if [ -z "$OPENAI_API_KEY" ]; then
#     echo "Error: OPENAI_API_KEY is not set"
#     exit 1
# fi

# if [ -z "$VERTEX_PROJECT" ]; then
#     echo "Error: VERTEXAI_PROJECT is not set"
#     exit 1
# fi

# if [ -z "$VERTEX_LOCATION" ]; then
#     echo "Error: VERTEXAI_LOCATION is not set"
#     exit 1
# fi

# if [ -z "$LITELLM_MASTER_KEY" ]; then
#     echo "Error: LITELLM_MASTER_KEY is not set"
#     exit 1
# fi

# Start the LiteLLM proxy with the config file
litellm --config config.yaml --detailed_debug
