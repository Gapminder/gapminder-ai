import json

prompts = [
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "user", "content": "Write a hello world program in Python"},
    {"role": "user", "content": "Explain what is machine learning in simple terms"},
    {
        "role": "user",
        "content": "What is the difference between SQL and NoSQL databases?",
    },
    {"role": "user", "content": "How do I make a chocolate cake?"},
]

# Create a single batch request
batch_request = {"model": "claude-3-sonnet-20240229", "messages": prompts}

with open("batch_prompts.json", "w") as f:
    json.dump(batch_request, f, indent=2)
