import os
import pytest
from unittest.mock import patch
from garak.generators.mistral import MistralGenerator

DEFAULT_DEPLOYMENT_NAME = "mistral-small-latest"

@patch.dict(os.environ, {"MISTRAL_API_KEY": "fake_api_key"})
@patch("garak.generators.mistral.MistralGenerator.generate")
def test_mistral_generator(mock_generate):
    # Définir le retour simulé
    mock_generate.return_value = ["Mocked response"]

    # Initialiser le générateur
    generator = MistralGenerator()

    # Appeler la méthode générer
    output = generator.generate("Test prompt")

    # Vérifier que la fonction a bien été appelée
    mock_generate.assert_called_once_with("Test prompt")

    # Vérifier le résultat
    assert output == ["Mocked response"]

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
