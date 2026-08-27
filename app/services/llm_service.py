import os

from groq import Groq


def get_llm_client() -> Groq:
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise ValueError(
            "LLM_API_KEY is not configured"
        )

    return Groq(api_key=api_key)


def generate_answer(
    question: str,
    context: str,
) -> str:

    client = get_llm_client()

    model = os.getenv(
        "LLM_MODEL",
        "llama-3.1-8b-instant",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the SmartFoodOps restaurant assistant. "
                    "Answer questions using only the provided restaurant "
                    "menu context. If the answer is not present in the "
                    "context, clearly say that the information is not "
                    "available. Do not invent menu items, prices, "
                    "availability, restaurants, or ingredients."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Restaurant menu context:\n\n"
                    f"{context}\n\n"
                    f"Customer question:\n"
                    f"{question}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=500,
    )

    return response.choices[0].message.content