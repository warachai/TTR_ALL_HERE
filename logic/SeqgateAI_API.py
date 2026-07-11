import requests
import json
import os
import argparse
from pathlib import Path

#API_KEY = os.getenv("SEAGATE_GENAI_API_KEY", "S57ipZivMtC2iuDCWqdy3edIPX-MwgBH") #mmm
API_KEY = os.getenv("SEAGATE_GENAI_API_KEY", "JvolwssXVoiyHXuHFT1IN9EM2ZYR9PRw")
BASE_URL = os.getenv("SEAGATE_GENAI_BASE_URL", "https://genai-models.seagate.com")
CHAT_COMPLETIONS_PATH = "/openai/v1/chat/completions"


def read_csv_text(csv_path: Path, max_chars: int = 120000):
    with csv_path.open("r", encoding="utf-8-sig", errors="replace") as file:
        text = file.read()

    is_truncated = len(text) > max_chars
    if is_truncated:
        text = text[:max_chars]
    return text, is_truncated


def _build_headers(api_key: str):
    if not api_key:
        raise ValueError("Missing API key. Set SEAGATE_GENAI_API_KEY in your environment.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def analyze_text(
    question: str,
    data_text: str,
    data_name: str = "session_data.txt",
    model: str = "gpt-4.1-mini",
    max_chars: int = 120000,
    temperature: float = 0.2,
    timeout: int = 60,
    api_key: str | None = None,
    base_url: str | None = None,
):
    if data_text is None:
        raise ValueError("data_text is required")

    resolved_api_key = api_key or API_KEY
    resolved_base_url = (base_url or BASE_URL).rstrip("/")
    headers = _build_headers(resolved_api_key)

    is_truncated = len(data_text) > max_chars
    text_payload = data_text[:max_chars] if is_truncated else data_text
    truncation_note = "\n\nNote: Input content was truncated due to size limit." if is_truncated else ""

    user_prompt = (
        f"{question}\n\n"
        f"Data source: {data_name}\n"
        f"Data content:\n{text_payload}{truncation_note}"
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": """
You are a factory analytics AI.

Analyze the provided dataset.

You MUST ALWAYS return valid JSON only.

Response schema:

{
  "status": "success",
  "confidence": "high",

  "summary": [
    "..."
  ],

  "findings": [
    {
      "operation": "",
      "state": "",
      "message": "",
      "difference": 0
    }
  ],

  "anomalies": [
    {
      "operation": "",
      "state": "",
      "message": "",
      "difference": 0
    }
  ],

  "recommendations": [
    "..."
  ],

  "required_data": [
    "..."
  ]
}

Rules:

- Return JSON only.
- Do not add explanation outside JSON.
- required_data must contain the next data required for deeper analysis.
- If analysis is sufficient set required_data=[]."""
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": temperature
    }

    response = requests.post(
        f"{resolved_base_url}{CHAT_COMPLETIONS_PATH}",
        headers=headers,
        json=payload,
        timeout=timeout
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        # Include API response body to make endpoint/auth/payload problems visible.
        print(f"HTTP {response.status_code} error from {response.url}")
        print(response.text)
        raise

    result = response.json()
    content = result["choices"][0]["message"]["content"]
    return result, content


def analyze_csv_file(
    question: str,
    csv_path: Path,
    model: str = "gpt-4.1-mini",
    max_chars: int = 120000,
    temperature: float = 0.2,
    timeout: int = 60,
    api_key: str | None = None,
    base_url: str | None = None,
):
    """Backward-compatible wrapper for file-based usage."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    csv_text, _ = read_csv_text(csv_path, max_chars=max_chars)
    return analyze_text(
        question=question,
        data_text=csv_text,
        data_name=csv_path.name,
        model=model,
        max_chars=max_chars,
        temperature=temperature,
        timeout=timeout,
        api_key=api_key,
        base_url=base_url,
    )


def main():
    parser = argparse.ArgumentParser(description="Analyze CSV data using Seagate GenAI API")
    parser.add_argument(
        "--question",
        default="What are the key insights from the test time summary data?",
        help="Question to ask about the CSV data"
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Input text content to analyze"
    )
    parser.add_argument(
        "--data-name",
        default="session_data.txt",
        help="Logical name for the input data"
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="Model name"
    )
    args = parser.parse_args()

    result, content = analyze_text(
        question=args.question,
        data_text=args.text,
        data_name=args.data_name,
        model=args.model,
    )

    print(json.dumps(result, indent=2))
    print(content)



if __name__ == "__main__":
    main()

