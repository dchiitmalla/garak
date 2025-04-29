# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest


@pytest.fixture(autouse=True)
def clear_langprovider_state(request):
    """Reset langprovider for each test"""

    def clear_langprovider_state():
        import gc
        import importlib
        from garak import langservice, _config

        for _, v in langservice.langproviders.items():
            del v
        langservice.langproviders = {}
        # reset defaults for langprovider _config
        importlib.reload(_config)
        gc.collect()

    request.addfinalizer(clear_langprovider_state)


def enable_gpu_testing():
    # enable GPU testing in dev env
    # should this just be an env variable check to allows faster local testing?
    import torch

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available() else "cpu"
    )

    if device == "mps":
        import psutil

        if psutil.virtual_memory().total < (16 * 1024**3):
            device = "cpu"  # fallback when less than 16GB of unified memory

    from garak.langproviders.local import LocalHFTranslator

    LocalHFTranslator.DEFAULT_PARAMS["hf_args"]["device"] = device


enable_gpu_testing()
