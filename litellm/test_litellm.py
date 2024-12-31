import os
import asyncio
import litellm


async def test_batch_api():
    # Step 1: Create file for batch completion
    file_response = await litellm.acreate_file(
        file=open("litellm/batch_prompts.jsonl", "rb"),
        purpose="batch",
        custom_llm_provider="openai",
    )
    print("File created:", file_response)

    # Step 2: Create batch request
    batch_response = await litellm.acreate_batch(
        completion_window="24h",
        endpoint="/v1/chat/completions",
        input_file_id=file_response.id,
        custom_llm_provider="openai",
        metadata={"test": "litellm_batch_test"},
    )
    print("Batch created:", batch_response)

    # Step 3: Retrieve batch status
    retrieved_batch = await litellm.aretrieve_batch(
        batch_id=batch_response.id, custom_llm_provider="openai"
    )
    print("Retrieved batch:", retrieved_batch)

    # Step 4: Get file content
    content = await litellm.afile_content(
        file_id=file_response.id, custom_llm_provider="openai"
    )
    print("File content:", content)

    # Step 5: List batches
    batches = litellm.list_batches(custom_llm_provider="openai", limit=10)
    print("List of batches:", batches)


if __name__ == "__main__":
    # Set LiteLLM proxy URL
    os.environ["OPENAI_API_BASE"] = "http://localhost:4000"
    os.environ["OPENAI_API_KEY"] = "sk-12341234"  # Use your LiteLLM proxy key

    asyncio.run(test_batch_api())
