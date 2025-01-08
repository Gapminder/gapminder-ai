import litellm
import os
import asyncio
import time


async def main():
    os.environ["OPENAI_API_KEY"] = "sk-12341234"
    litellm.api_base = "http://localhost:4000"

    file_name = "batch_prompts.jsonl"
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(_current_dir, file_name)
    file_obj = await litellm.acreate_file(
        file=open(file_path, "rb"),
        purpose="batch",
        custom_llm_provider="openai",
    )
    print("Response from creating file=", file_obj)

    create_batch_response = await litellm.acreate_batch(
        completion_window="24h",
        endpoint="/v1/chat/completions",
        input_file_id=file_obj.id,
        custom_llm_provider="openai",
        metadata={"custom_id": "test_batch_1"},
    )

    print("response from litellm.create_batch=", create_batch_response)

    batch_id = create_batch_response.id
    # batch_id = "batch_677de66faf988190a417909b0deda9a9"

    while True:
        batch_status = await litellm.aretrieve_batch(
            batch_id, custom_llm_provider="openai"
        )

        if batch_status.output_file_id:
            content = await litellm.afile_content(
                batch_status.output_file_id, custom_llm_provider="openai"
            )
            print(content)
            break
        else:
            time.sleep(100)


if __name__ == "__main__":
    asyncio.run(main())
