# SPDX-FileCopyrightText: Portions Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from garak.resources.fixer import Migration
from garak.resources.fixer import _plugin


class RenameFigstep_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename FigStep probes to make lightweight the default"""

        path = ["plugins", "probes", "visual_jailbreak"]
        old = "FigStep"
        new = "FigStepFull"
        return _plugin.rename(config_dict, path, old, new)

class RenameFigstep_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename FigStep probes to make lightweight the default"""

        path = ["plugins", "probes", "visual_jailbreak"]
        old = "FigStepTiny"
        new = "FigStep"
        return _plugin.rename(config_dict, path, old, new)
