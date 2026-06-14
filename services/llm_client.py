import os
import json

from openai import OpenAI


OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

if not OPENROUTER_API_KEY:

    raise ValueError(
        "OPENROUTER_API_KEY not found."
    )


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)


MODEL_NAME = "qwen/qwen3-32b"


def ask_llm_json(prompt):

    response = (
        client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role":"user",
                    "content":prompt
                }
            ],
            temperature=0
        )
    )

    content = (
        response
        .choices[0]
        .message.content
    )

    return json.loads(
        content
    )
