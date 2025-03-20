DEFAULT_CLASS = "MistralGenerator"
import os
from garak.generators.base import Generator
import garak._config as _config
from mistralai import Mistral


class MistralGenerator(Generator):
    generator_family_name = "mistral"
    fullname = "Mistral AI"
    supports_multiple_generations = False

    def __init__(self, name="mistral-large-latest", config_root=_config):
        self.name = name
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError(
                "Please define mistral api key by defining environment variable MISTRAL_API_KEY"
            )
        self.client = Mistral(api_key=api_key)

    def _call_model(self, prompt, generations_this_call=1):
        chat_response = self.client.chat.complete(
            model=self.name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        return [chat_response.choices[0].message.content]
