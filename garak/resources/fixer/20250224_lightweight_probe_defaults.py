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


class RenameGraphConn_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.graphconnectivity probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "GraphConnectivity"
        new = "GraphConnectivityFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameGraphConn_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.graphconnectivity probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "GraphConnectivityMini"
        new = "GraphConnectivity"
        return _plugin.rename(config_dict, path, old, new)


class RenamePrimes_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.primes probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "Prime"
        new = "PrimesFull"
        return _plugin.rename(config_dict, path, old, new)


class RenamePrimes_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.primes probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "PrimesMini"
        new = "Primes"
        return _plugin.rename(config_dict, path, old, new)


class RenameSenators_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.senators probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "Senators"
        new = "SenatorsFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameSenators_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename snowball.senators probes to make lightweight the default"""

        path = ["plugins", "probes", "snowball"]
        old = "SenatorsMini"
        new = "Senators"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackHateHumans_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackHateHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackHateHumans"
        new = "HijackHateHumansFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackHateHumans_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackHateHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackHateHumansMini"
        new = "HijackHateHumans"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackKillHumans_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackKillHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackKillHumans"
        new = "HijackKillHumansFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackKillHumans_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackKillHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackKillHumansMini"
        new = "HijackKillHumans"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackLongPrompt_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackKillHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackLongPrompt"
        new = "HijackLongPromptFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackLongPrompt_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackLongPrompt probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackLongPromptMini"
        new = "HijackLongPrompt"
        return _plugin.rename(config_dict, path, old, new)


class RenameHijackLongPrompt_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename promptinject.HijackKillHumans probes to make lightweight the default"""

        path = ["plugins", "probes", "promptinject"]
        old = "HijackLongPrompt"
        new = "HijackLongPromptFull"
        return _plugin.rename(config_dict, path, old, new)


class RenamePastTense_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename phrasing.PastTense probes to make lightweight the default"""

        path = ["plugins", "probes", "phrasing"]
        old = "PastTense"
        new = "PastTenseFull"
        return _plugin.rename(config_dict, path, old, new)


class RenamePastTense_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename phrasing.PastTense probes to make lightweight the default"""

        path = ["plugins", "probes", "phrasing"]
        old = "PastTenseMini"
        new = "PastTense"
        return _plugin.rename(config_dict, path, old, new)


class RenameFutureTense_1(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename phrasing.FutureTense probes to make lightweight the default"""

        path = ["plugins", "probes", "phrasing"]
        old = "FutureTense"
        new = "FutureTenseFull"
        return _plugin.rename(config_dict, path, old, new)


class RenameFutureTense_2(Migration):
    def apply(config_dict: dict) -> dict:
        """Rename phrasing.FutureTense probes to make lightweight the default"""

        path = ["plugins", "probes", "phrasing"]
        old = "FutureTenseMini"
        new = "FutureTense"
        return _plugin.rename(config_dict, path, old, new)
