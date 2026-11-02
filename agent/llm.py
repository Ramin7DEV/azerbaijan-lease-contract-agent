"""Model ilə danışan yeganə modul. Model və provayder .env-dən gəlir."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    api_key=os.getenv("LLM_API_KEY") or "açar-yoxdur",  # import açarsız da işləsin (testlər)
    timeout=300,  # tam təhlil 1–2 dəqiqə çəkir
    max_retries=3,  # 429 / 5xx / şəbəkə xətalarında klient özü gözləyib təkrarlayır
)
MODEL = os.getenv("LLM_MODEL", "gemma-4-31b-it")


def ask(system: str, user: str, json_mode: bool = False, max_tokens: int | None = None) -> str:
    """System prompt (sabit hissə) + istifadəçi mesajı (dəyişən hissə) → cavab mətni."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        **({"max_tokens": max_tokens} if max_tokens else {}),
        response_format={"type": "json_object"} if json_mode else None,
    )
    text = response.choices[0].message.content if response.choices else None
    if not text:
        raise ValueError("Model boş cavab qaytardı")
    # Gemma cavabdan əvvəl <thought>...</thought> blokunda düşünür — onu atırıq.
    return text.split("</thought>")[-1].strip()


if __name__ == "__main__":
    print(f"Model: {MODEL}\n")
    print(
        ask(
            "Sən Azərbaycan hüquqşünasısan. Qısa və yalnız Azərbaycan dilində cavab ver.",
            "Bu icarə bəndi icarəçi üçün risklidirmi? 'İcarəyə verən istənilən vaxt, "
            "səbəb göstərmədən müqaviləni ləğv edə bilər.' 3 cümlə ilə izah et.",
        )
    )
