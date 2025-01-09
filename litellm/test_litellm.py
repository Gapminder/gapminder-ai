import os
import openai
import time


# cert = load_vertex_ai_credentials()
# print(cert)

oai_client = openai.OpenAI(
    api_key="sk-12341234",  # litellm proxy API key
    base_url="http://localhost:4000",  # litellm proxy base url
)


def main():
    # os.environ["OPENAI_API_KEY"] = "sk-12341234"
    # litellm.api_base = "http://localhost:4000"

    file_name = "batch_prompts.jsonl"
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(_current_dir, file_name)
    # file_obj = await litellm.acreate_file(
    #     file=open(file_path, "rb"),
    #     purpose="batch",
    #     custom_llm_provider="vertex_ai",
    # )
    file_obj = oai_client.files.create(
        file=open(file_path, "rb"),
        purpose="batch",
        extra_body={
            "custom_llm_provider": "vertex_ai"
        },  # tell litellm to use vertex_ai for this file upload
    )
    print("Response from creating file=", file_obj)

    # create_batch_response = await litellm.acreate_batch(
    #     completion_window="24h",
    #     endpoint="/v1/chat/completions",
    #     input_file_id=file_obj.id,
    #     custom_llm_provider="openai",
    #     metadata={"custom_id": "test_batch_1"},
    # )
    batch_input_file_id = file_obj.id  # use `file_obj` from step 2
    create_batch_response = oai_client.batches.create(
        completion_window="24h",
        endpoint="/v1/chat/completions",
        input_file_id=batch_input_file_id,
        extra_body={"custom_llm_provider": "vertex_ai"},
    )

    print("response from litellm.create_batch=", create_batch_response)

    batch_id = create_batch_response.id

    while True:
        batch_status = oai_client.batches.retrieve(
            batch_id, extra_body={"custom_llm_provider": "vertex_ai"}
        )

        if batch_status.output_file_id:
            content = oai_client.files.content(
                batch_status.output_file_id,
                extra_body={"custom_llm_provider": "vertex_ai"},
            )
            content.write_to_file("./test_output_2.json")
            break
        else:
            time.sleep(100)

    # while True:
    #     batch_status = await litellm.aretrieve_batch(
    #         batch_id, custom_llm_provider="openai"
    #     )

    #     if batch_status.output_file_id:
    #         content = await litellm.afile_content(
    #             batch_status.output_file_id, custom_llm_provider="openai"
    #         )
    #         content.write_to_file("./test_output.json")
    #         break
    #     else:
    #         time.sleep(100)


if __name__ == "__main__":
    main()
