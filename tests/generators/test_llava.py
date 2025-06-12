import os
import pytest
import torch
from pathlib import Path
from PIL import Image, ImageDraw

from garak._config import GarakSubConfig
from garak.generators.huggingface import LLaVA
from garak.exception import ModelNameMissingError

# Constants for test image
IMG_WIDTH = 300
IMG_HEIGHT = 200
RECT_COORDS = ((50, 50), (200, 150))
ELLIPSE_COORDS = ((150, 50), (250, 150))

# Force CPU testing via environment variable
FORCE_CPU = os.getenv("FORCE_LLAVA_CPU", "0") == "1"

# Skip tests if no CUDA and not forcing CPU, or when running in CI
pytestmark = [
    pytest.mark.skipif(
        not torch.cuda.is_available() and not FORCE_CPU,
        reason="Requires CUDA or FORCE_LLAVA_CPU=1"
    ),
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="Skipping LLaVA tests in CI environment"
    ),
]


def _is_memory_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "out of memory" in msg or "cuda out of memory" in msg


@pytest.fixture
def test_image(tmp_path):
    """Generate a simple RGB image with basic shapes and return its path."""
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle(RECT_COORDS, fill=(255, 0, 0))
    draw.ellipse(ELLIPSE_COORDS, fill=(0, 0, 255))

    file_path = tmp_path / "test.png"
    img.save(file_path)
    return str(file_path)


@pytest.fixture
def hf_gpu_config():
    """Create a HuggingFace generator config for CPU or GPU."""
    dtype = "float32" if FORCE_CPU else "float16"
    hf_args = {
        "torch_dtype": dtype,
        "device_map": "auto",
        "low_cpu_mem_usage": True,
    }

    config_root = GarakSubConfig()
    config_root.generators = {"huggingface": {"hf_args": hf_args}}
    return config_root


@pytest.mark.parametrize("model_name", [
    "llava-hf/llava-v1.6-34b-hf",
    "llava-hf/llava-v1.6-vicuna-13b-hf",
    "llava-hf/llava-v1.6-vicuna-7b-hf",
    "llava-hf/llava-v1.6-mistral-7b-hf",
])
def test_llava_instantiation(hf_gpu_config, model_name):
    """Verify that LLaVA instantiates correctly and uses the right device."""
    try:
        llava = LLaVA(name=model_name, config_root=hf_gpu_config)
        assert llava.name == model_name
        assert hasattr(llava, "model")
        assert hasattr(llava, "processor")

        # Device type assertion
        expected = "cpu" if FORCE_CPU else "cuda"
        assert llava.device.type == expected
    except Exception as exc:
        if _is_memory_error(exc):
            pytest.skip(f"OOM instantiating {model_name}: {exc}")
        raise


@pytest.mark.parametrize("model_name", [
    "llava-hf/llava-v1.6-34b-hf",
    "llava-hf/llava-v1.6-vicuna-13b-hf",
    "llava-hf/llava-v1.6-vicuna-7b-hf",
    "llava-hf/llava-v1.6-mistral-7b-hf",
])
def test_llava_generate(hf_gpu_config, test_image, model_name):
    """Verify that LLaVA can generate text responses given a text+image prompt."""
    prompt = {
        "text": "Describe the shapes and colors in this image.",
        "image": test_image,
    }

    try:
        llava = LLaVA(name=model_name, config_root=hf_gpu_config)
        responses = llava.generate(prompt, generations_this_call=1)

        assert isinstance(responses, list)
        assert len(responses) == 1
        assert isinstance(responses[0], str) and responses[0]
    except Exception as exc:
        if _is_memory_error(exc):
            pytest.skip(f"OOM generating with {model_name}: {exc}")
        raise


@pytest.mark.parametrize("model_name", [
    "llava-hf/llava-v1.6-34b-hf",
    "llava-hf/llava-v1.6-vicuna-13b-hf",
    "llava-hf/llava-v1.6-vicuna-7b-hf",
    "llava-hf/llava-v1.6-mistral-7b-hf",
])
def test_llava_error_handling(hf_gpu_config, model_name):
    """Ensure generate() raises FileNotFoundError for invalid image paths."""
    invalid_prompt = {"text": "Describe this image.", "image": "/nonexistent.png"}
    try:
        llava = LLaVA(name=model_name, config_root=hf_gpu_config)
        with pytest.raises(FileNotFoundError):
            llava.generate(invalid_prompt)
    except Exception as exc:
        if _is_memory_error(exc):
            pytest.skip(f"OOM instantiating {model_name}: {exc}")
        raise


def test_llava_unsupported_model(hf_gpu_config):
    """Instantiating with an unsupported model name should error."""
    with pytest.raises(ModelNameMissingError):
        LLaVA(name="unsupported-model-name", config_root=hf_gpu_config)

# To force CPU execution without CUDA, set: FORCE_LLAVA_CPU=1 pytest -v
