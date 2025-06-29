"""garak global config"""

# SPDX-FileCopyrightText: Portions Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# plugin code < base config < site config < run config < cli params

# logging should be set up before config is loaded

import platform
from collections import defaultdict
from dataclasses import dataclass
import importlib
import json
import logging
import os
import stat
import pathlib
from typing import Dict, List, Any, Set
import yaml
from xdg_base_dirs import (
    xdg_cache_home,
    xdg_config_home,
    xdg_data_home,
)

DICT_CONFIG_AFTER_LOAD = False

from garak import __version__ as version

system_params = (
    "verbose narrow_output parallel_requests parallel_attempts skip_unknown".split()
)
run_params = "seed deprefix eval_threshold generations probe_tags interactive".split()
plugins_params = "model_type model_name extended_detectors".split()
reporting_params = "taxonomy report_prefix".split()
project_dir_name = "garak"


loaded = False


@dataclass
class GarakSubConfig:
    pass


@dataclass
class BuffManager:
    """class to store instantiated buffs"""

    buffs = []


@dataclass
class TransientConfig(GarakSubConfig):
    """Object to hold transient global config items not set externally"""

    log_filename = None
    report_filename = None
    reportfile = None
    hitlogfile = None
    args = None  # only access this when determining what was passed on CLI
    run_id = None
    package_dir = pathlib.Path(__file__).parents[0]
    config_dir = xdg_config_home() / project_dir_name
    data_dir = xdg_data_home() / project_dir_name
    cache_dir = xdg_cache_home() / project_dir_name
    starttime = None
    starttime_iso = None

    # initialize the user home and cache paths if they do not exist
    config_dir.mkdir(mode=0o740, parents=True, exist_ok=True)
    data_dir.mkdir(mode=0o740, parents=True, exist_ok=True)
    cache_dir.mkdir(mode=0o740, parents=True, exist_ok=True)


transient = TransientConfig()

system = GarakSubConfig()
run = GarakSubConfig()
plugins = GarakSubConfig()
reporting = GarakSubConfig()


def _lock_config_as_dict():
    global plugins
    for plugin_type in ("probes", "generators", "buffs", "detectors", "harnesses"):
        setattr(plugins, plugin_type, _crystallise(getattr(plugins, plugin_type)))


def _crystallise(d):
    for k in d.keys():
        if isinstance(d[k], defaultdict):
            d[k] = _crystallise(d[k])
    return dict(d)


def _nested_dict():
    return defaultdict(nested_dict)


nested_dict = _nested_dict

plugins.probes = nested_dict()
plugins.generators = nested_dict()
plugins.detectors = nested_dict()
plugins.buffs = nested_dict()
plugins.harnesses = nested_dict()
reporting.taxonomy = None  # set here to enable report_digest to be called directly

buffmanager = BuffManager()

config_files = []

# this is so popular, let's set a default. what other defaults are worth setting? what's the policy?
run.seed = None
run.soft_probe_prompt_cap = 64
run.target_lang = "en"
run.langproviders = []

# placeholder
# generator, probe, detector, buff = {}, {}, {}, {}


def _key_exists(d: dict, key: str) -> bool:
    # Check for the presence of a key in a nested dict.
    if not isinstance(d, dict) and not isinstance(d, list):
        return False
    if isinstance(d, list):
        return any([_key_exists(item, key) for item in d])
    if isinstance(d, dict) and key in d.keys():
        return True
    else:
        return any([_key_exists(val, key) for val in d.values()])


def _set_settings(config_obj, settings_obj: dict):
    for k, v in settings_obj.items():
        setattr(config_obj, k, v)
    return config_obj


def _combine_into(d: dict, combined: dict) -> dict:
    if d is None:
        return combined
    for k, v in d.items():
        if isinstance(v, dict):
            _combine_into(v, combined.setdefault(k, nested_dict()))
        else:
            combined[k] = v
    return combined


def _load_yaml_config(settings_filenames) -> dict:
    global config_files
    config_files += settings_filenames
    config = nested_dict()
    for settings_filename in settings_filenames:
        with open(settings_filename, encoding="utf-8") as settings_file:
            settings = yaml.safe_load(settings_file)
            if settings is not None:
                if _key_exists(settings, "api_key"):
                    if platform.system() == "Windows":
                        msg = (
                            f"A possibly secret value (`api_key`) was detected in {settings_filename}. "
                            f"We recommend removing potentially sensitive values from config files or "
                            f"ensuring the file is readable only by you."
                        )
                        logging.warning(msg)
                        print(f"⚠️  {msg}")
                    else:
                        logging.info(
                            f"API key found in {settings_filename}. Checking readability..."
                        )
                        res = os.stat(settings_filename)
                        if res.st_mode & stat.S_IROTH or res.st_mode & stat.S_IRGRP:
                            msg = (
                                f"A possibly secret value (`api_key`) was detected in {settings_filename}, "
                                f"which is readable by users other than yourself. "
                                f"Consider changing permissions on this file to only be readable by you."
                            )
                            logging.warning(msg)
                            print(f"⚠️  {msg}")
                config = _combine_into(settings, config)
    return config


def _store_config(settings_files) -> None:
    global system, run, plugins, reporting, version
    settings = _load_yaml_config(settings_files)
    system = _set_settings(system, settings["system"])
    run = _set_settings(run, settings["run"])
    run.user_agent = run.user_agent.replace("{version}", version)
    plugins = _set_settings(plugins, settings["plugins"])
    reporting = _set_settings(reporting, settings["reporting"])


# not my favourite solution in this module, but if
# _config.set_http_lib_agents() to be predicated on a param instead of
# a _config.run value (i.e. user_agent) - which it needs to be if it can be
# used when the values are popped back to originals - then a separate way
# of passing the UA string to _garak_user_agent() needs to exist, outside of
# _config.run.user_agent
REQUESTS_AGENT = ""


def _garak_user_agent(dummy=None):
    return str(REQUESTS_AGENT)


def set_all_http_lib_agents(agent_string):
    set_http_lib_agents(
        {"requests": agent_string, "httpx": agent_string, "aiohttp": agent_string}
    )


def set_http_lib_agents(agent_strings: dict):

    global REQUESTS_AGENT

    if "requests" in agent_strings:
        from requests import utils

        REQUESTS_AGENT = agent_strings["requests"]
        utils.default_user_agent = _garak_user_agent
    if "httpx" in agent_strings:
        import httpx

        httpx._client.USER_AGENT = agent_strings["httpx"]
    if "aiohttp" in agent_strings:
        import aiohttp

        aiohttp.client_reqrep.SERVER_SOFTWARE = agent_strings["aiohttp"]


def get_http_lib_agents():
    from requests import utils
    import httpx
    import aiohttp

    agent_strings = {}
    agent_strings["requests"] = utils.default_user_agent
    agent_strings["httpx"] = httpx._client.USER_AGENT
    agent_strings["aiohttp"] = aiohttp.client_reqrep.SERVER_SOFTWARE

    return agent_strings


def load_base_config() -> None:
    global loaded
    settings_files = [str(transient.package_dir / "resources" / "garak.core.yaml")]
    logging.debug("Loading configs from: %s", ",".join(settings_files))
    _store_config(settings_files=settings_files)
    loaded = True


def load_config(
    site_config_filename="garak.site.yaml", run_config_filename=None
) -> None:
    # would be good to bubble up things from run_config, e.g. generator, probe(s), detector(s)
    # and then not have cli be upset when these are not given as cli params
    global loaded

    settings_files = [str(transient.package_dir / "resources" / "garak.core.yaml")]

    fq_site_config_filename = str(transient.config_dir / site_config_filename)
    if os.path.isfile(fq_site_config_filename):
        settings_files.append(fq_site_config_filename)
    else:
        # warning, not error, because this one has a default value
        logging.debug("no site config found at: %s", fq_site_config_filename)

    if run_config_filename is not None:
        # take config file path as provided
        if os.path.isfile(run_config_filename):
            settings_files.append(run_config_filename)
        elif os.path.isfile(
            str(transient.package_dir / "configs" / (run_config_filename + ".yaml"))
        ):
            settings_files.append(
                str(transient.package_dir / "configs" / (run_config_filename + ".yaml"))
            )
        else:
            message = f"run config not found: {run_config_filename}"
            logging.error(message)
            raise FileNotFoundError(message)

    logging.debug("Loading configs from: %s", ",".join(settings_files))
    _store_config(settings_files=settings_files)

    if DICT_CONFIG_AFTER_LOAD:
        _lock_config_as_dict()
    loaded = True


def parse_plugin_spec(
    spec: str, category: str, probe_tag_filter: str = ""
) -> tuple[List[str], List[str]]:
    from garak._plugins import enumerate_plugins

    if spec is None or spec.lower() in ("", "auto", "none"):
        return [], []
    unknown_plugins = []
    if spec.lower() in ("all", "*"):
        plugin_names = [
            name
            for name, active in enumerate_plugins(category=category)
            if active is True
        ]
    else:
        plugin_names = []
        for clause in spec.split(","):
            if clause.count(".") < 1:
                found_plugins = [
                    p
                    for p, a in enumerate_plugins(category=category)
                    if p.startswith(f"{category}.{clause}.") and a is True
                ]
                if len(found_plugins) > 0:
                    plugin_names += found_plugins
                else:
                    unknown_plugins += [clause]
            else:
                # validate the class exists
                found_plugins = [
                    p
                    for p, a in enumerate_plugins(category=category)
                    if p == f"{category}.{clause}"
                ]
                if len(found_plugins) > 0:
                    plugin_names += found_plugins
                else:
                    unknown_plugins += [clause]

    if probe_tag_filter is not None and len(probe_tag_filter) > 1:
        plugins_to_skip = []
        for plugin_name in plugin_names:
            plugin_module_name = ".".join(plugin_name.split(".")[:-1])
            plugin_class_name = plugin_name.split(".")[-1]
            m = importlib.import_module(f"garak.{plugin_module_name}")
            c = getattr(m, plugin_class_name)
            if not any([tag.startswith(probe_tag_filter) for tag in c.tags]):
                plugins_to_skip.append(
                    plugin_name
                )  # using list.remove doesn't update for-loop position

        for plugin_to_skip in plugins_to_skip:
            plugin_names.remove(plugin_to_skip)

    return plugin_names, unknown_plugins


# Fields that should be excluded from config serialization
_EXCLUDED_CONFIG_FIELDS: Set[str] = {
    # API keys and secrets
    "api_key", 
    "OPENAI_API_KEY", 
    "AZURE_OPENAI_API_KEY", 
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY", 
    "ENV_VAR",
    
    # Transient runtime values
    "reportfile", 
    "hitlogfile", 
    "args", 
    "package_dir",
    "log_filename", 
    "starttime", 
    "starttime_iso",
    
    # Constants and internal implementations
    "_crystallise", 
    "_nested_dict", 
    "nested_dict", 
    "REQUESTS_AGENT",
    "_garak_user_agent", 
    "_key_exists", 
    "_set_settings", 
    "_combine_into",
    "_store_config",
}


def serialize_config() -> Dict[str, Any]:
    """
    Centralized function to serialize garak configuration, excluding sensitive and unnecessary data.
    
    This function handles serializing the configuration in a way that:
    1. Excludes API keys, secrets, and other sensitive data
    2. Excludes implementation details, constants, and runtime objects
    3. Includes only the data necessary to reproduce a run
    
    Returns:
        Dict[str, Any]: A dictionary containing the serialized configuration
    """
    # Create base dictionary with entry type
    config_dict = {"entry_type": "start_run setup"}
    
    # Helper function to determine if a value is serializable
    def is_serializable(value: Any) -> bool:
        return type(value) in (
            str, int, float, bool, dict, tuple, list, set, type(None)
        ) or isinstance(value, (str, int, float, bool, dict, tuple, list, set))
    
    # Helper function to check if a field should be excluded
    def should_exclude(key: str) -> bool:
        # Check direct matches
        if key in _EXCLUDED_CONFIG_FIELDS:
            return True
            
        # Check for API keys with partial matching
        key_lower = key.lower()
        if any(term in key_lower for term in ["api_key", "password", "secret", "token"]):
            return True
            
        # Exclude private members
        if key.startswith("_") and key != "_config":
            return True
            
        return False
    
    # Process top-level attributes of _config
    for k, v in globals().items():
        if k[:2] != "__" and is_serializable(v) and not should_exclude(k):
            config_dict[f"_config.{k}"] = v
    
    # Process attributes in the main config submodules
    for subset in "system run plugins reporting".split():
        if subset in globals():
            subset_obj = globals()[subset]
            for k, v in subset_obj.__dict__.items():
                if k[:2] != "__" and is_serializable(v) and not should_exclude(k):
                    config_dict[f"{subset}.{k}"] = v
    
    # Include only specific transient values that matter for reproducibility
    if "transient" in globals():
        for k, v in transient.__dict__.items():
            if k in ["run_id", "config_dir", "data_dir", "cache_dir", "report_filename"] and is_serializable(v):
                config_dict[f"transient.{k}"] = v
    
    return config_dict


def serialize_config_to_json() -> str:
    """
    Serialize the config and return it as a JSON string.
    
    Returns:
        str: JSON representation of the serialized config
    """
    return json.dumps(serialize_config(), ensure_ascii=False)
