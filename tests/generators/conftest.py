# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import pytest
import pathlib


@pytest.fixture
def openai_compat_mocks():
    """Mock responses for OpenAI compatible endpoints"""
    with open(pathlib.Path(__file__).parents[0] / "openai.json") as mock_openai:
        return json.load(mock_openai)


@pytest.fixture
def hf_endpoint_mocks():
    """Mock responses for Huggingface InferenceAPI based endpoints"""
    with open(pathlib.Path(__file__).parents[0] / "hf_inference.json") as mock_openai:
        return json.load(mock_openai)

@pytest.fixture
def watsonx_compat_mocks():
    """Mock responses for watsonx.ai based endpoints"""
    with open(pathlib.Path(__file__).parents[0] / "watsonx.json") as mock_watsonx:
        return json.load(mock_watsonx)

@pytest.fixture
def mistral_compat_mocks():
    """Mock responses for Mistral AI based endpoints"""
    with open(pathlib.Path(__file__).parents[0] / "mistral.json") as mock_mistral:
        return json.load(mock_mistral)

@pytest.fixture
def gemini_compat_mocks():
    """Mock responses for Google Gemini based endpoints"""
    with open(pathlib.Path(__file__).parents[0] / "gemini.json") as mock_gemini:
        return json.load(mock_gemini)