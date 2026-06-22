import os
import json
import httpx


class NvidiaLLMClient:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"

        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not set")

    async def generate(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Generic structured LLM call (expects JSON response)
        """

        payload = {
            "model": "meta/llama-3-70b-instruct",  # ✅ stable NVIDIA model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

            print("🧠 NVIDIA LLM STATUS:", response.status_code)

            response.raise_for_status()

            data = response.json()

            content = data["choices"][0]["message"]["content"]

            print("🧠 RAW LLM OUTPUT:", content)

            # ✅ enforce JSON parsing
            return json.loads(content)

        except Exception as e:
            print("❌ NVIDIA LLM ERROR:", str(e))

            return {
                "summary": "LLM unavailable",
                "probable_cause": "LLM error",
                "impact": "Unknown",
                "recommended_action": "Fallback to rule-based monitoring",
                "confidence": "low",
            }
