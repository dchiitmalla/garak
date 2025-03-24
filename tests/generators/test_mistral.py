import os
import pytest
from garak.generators.mistral import MistralGenerator

DEFAULT_DEPLOYMENT_NAME = "mistral-small-latest"

@pytest.mark.skipif(
    os.getenv(MistralGenerator.ENV_VAR, None) is None,
    reason=f"Mistral API key is not set in {MistralGenerator.ENV_VAR}",
)
def test_mistral_chat():
    generator = MistralGenerator(name=DEFAULT_DEPLOYMENT_NAME)
    assert generator.name == DEFAULT_DEPLOYMENT_NAME
    output = generator.generate("Hello Mistral!")
    assert len(output) == 1  # expect 1 generation by default
    print("test passed!")
