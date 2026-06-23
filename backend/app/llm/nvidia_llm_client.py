import os
import json
import httpx
import re


class NvidiaLLMClient:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")

        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"

        self.models = [
            "meta/llama-3.1-8b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.3-70b-instruct",
        ]

        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not set")

    def _extract_json(self, content: str):
        """
        Extract JSON from markdown or raw text
        """
        try:
            # ✅ Case 1: ```json ... ```
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # ✅ Case 2: any ``` ... ```
            match = re.search(r"```(.*?)```", content, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # ✅ Case 3: first {...} block (safe fallback)
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))

            # ✅ Case 4: raw JSON
            return json.loads(content)

        except Exception:
            return None

    async def generate(self, system_prompt: str, user_prompt: str) -> dict:

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for model in self.models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 800,
                }

                print(f"🧠 TRYING MODEL: {model}")

                async with httpx.AsyncClient(
                    timeout=30.0,
                    verify=False  # dev SSL fix
                ) as client:
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload,
                    )

                print("🧠 STATUS:", response.status_code)

                if response.status_code == 404:
                    print(f"❌ Model not found: {model}")
                    continue

                response.raise_for_status()

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                print("🧠 RAW OUTPUT:", content)

                parsed = self._extract_json(content)

                if parsed:
                    return parsed

                # ✅ fallback if parsing fails
                return {
                    "summary": content[:200],
                    "probable_cause": "Non-JSON LLM output",
                    "impact": "Parsing fallback",
                    "recommended_action": "Improve prompt format",
                    "confidence": "low",
                }

            except Exception as e:
                print(f"❌ Error with model {model}:", str(e))

        return {
            "summary": "LLM unavailable",
            "probable_cause": "All models failed",
            "impact": "Fallback mode",
            "recommended_action": "Check API / models",
            "confidence": "low",
        }