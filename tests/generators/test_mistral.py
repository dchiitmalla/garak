import os
import pytest
from garak.generators.mistral import MistralGenerator

DEFAULT_DEPLOYMENT_NAME = "mistral-small-latest"

@pytest.fixture
def set_fake_env(request) -> None:
    stored_env = os.getenv(MistralGenerator.ENV_VAR, None)

    def restore_env():
        if stored_env is not None:
            os.environ[MistralGenerator.ENV_VAR] = stored_env
        else:
            del os.environ[MistralGenerator.ENV_VAR]

    os.environ[MistralGenerator.ENV_VAR] = os.path.abspath(__file__)

    request.addfinalizer(restore_env)

@pytest.mark.skipif(
    os.getenv(MistralGenerator.ENV_VAR, None) is None,
    reason=f"OpenAI API key is not set in {MistralGenerator.ENV_VAR}",
)
def test_mistral_chat():
    generator = MistralGenerator(name=DEFAULT_DEPLOYMENT_NAME)
    assert generator.name == DEFAULT_DEPLOYMENT_NAME
    output = generator.generate("Hello Mistral!")
    assert len(output) == 1  # expect 1 generation by default
    print("test passed!")
