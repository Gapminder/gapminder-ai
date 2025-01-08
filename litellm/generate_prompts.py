import json

# Static configuration values
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7
# SYSTEM_FINGERPRINT = "fp_12345"

# List of prompt contents
PROMPT_CONTENTS = [
    "What is the capital of France?",
    "Write a hello world program in Python",
    "Explain what is machine learning in simple terms",
    "What is the difference between SQL and NoSQL databases?",
    "How do I make a chocolate cake?",
]

# Generate complete prompt objects
prompts = [
    {
        "custom_id": f"request-{i}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": MODEL,
            "messages": [
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": content}
            ],
            "temperature": TEMPERATURE,
        },
    }
    for i, content in enumerate(PROMPT_CONTENTS)
]

# Create a JSONL file with one prompt per line
with open("batch_prompts.jsonl", "w") as f:
    for prompt in prompts:
        f.write(json.dumps(prompt) + "\n")
