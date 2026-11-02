import httpx


class ProviderError(Exception):
    pass


class Provider:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=60, transport=transport)

    async def close(self):
        await self.client.aclose()

    async def answer(self, instructions, history):
        if not self.settings.ai_ready:
            raise ProviderError("AI settings are missing. Run configure.py on the host.")
        endpoints = {"openai": "https://api.openai.com/v1/responses",
                     "openrouter": "https://openrouter.ai/api/v1/responses"}
        if self.settings.provider not in endpoints:
            raise ProviderError("Unsupported AI provider. Run configure.py on the host.")
        try:
            response = await self.client.post(
                endpoints[self.settings.provider],
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                json={"model": self.settings.model, "instructions": instructions,
                      "input": history, "store": False, "max_output_tokens": self.settings.max_output},
            )
            if response.status_code != 200:
                message = {401: "API authentication failed. Check the selected provider's key on the host.",
                           402: "The AI provider needs credits or a higher key spending limit.",
                           403: "The API account cannot use this resource.",
                           404: "Model unavailable. Check the selected provider's model on the host.",
                           429: "API quota or rate limit reached. Try again later."}.get(
                               response.status_code, "The AI service could not complete the request.")
                raise ProviderError(message)
            data = response.json()
            if data.get("status") != "completed":
                raise ProviderError("The response was incomplete. Try a shorter question or adjust MAX_OUTPUT_TOKENS.")
            parts = []
            for item in data.get("output", []):
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            parts.append(part["text"])
                        elif part.get("type") == "refusal":
                            parts.append(part["refusal"])
            result = "\n".join(parts).strip()
            if not result:
                raise ProviderError("The AI service returned no text. Try rephrasing.")
            if len(result) > 5000:
                result = result[:4900] + "\n[Reply shortened. Ask for a specific section to continue.]"
            return result
        except httpx.TimeoutException:
            raise ProviderError("The AI request timed out. Try again later.") from None
        except httpx.RequestError:
            raise ProviderError("Could not connect to the AI service. Check your connection.") from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ProviderError("The AI service returned an unreadable response.") from None
