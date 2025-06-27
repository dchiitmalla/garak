# SPDX-FileCopyrightText: Portions Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import inspect

import garak
import garak._config
import garak._plugins
import garak.attempt
import garak.cli
import garak.probes.leakreplay


def test_leakreplay_hitlog():

    args = "-m test.Blank -p leakreplay -d always.Fail".split()
    garak.cli.main(args)


def test_leakreplay_output_count():
    generations = 1
    garak._config.load_base_config()
    garak._config.transient.reportfile = open(os.devnull, "w+")
    garak._config.plugins.probes["leakreplay"]["generations"] = generations
    a = garak.attempt.Attempt(prompt="test")
    p = garak._plugins.load_plugin(
        "probes.leakreplay.LiteratureCloze", config_root=garak._config
    )
    g = garak._plugins.load_plugin("generators.test.Blank", config_root=garak._config)
    p.generator = g
    results = p._execute_all([a])
    assert len(a.all_outputs) == generations


def test_leakreplay_handle_incomplete_attempt():
    p = garak.probes.leakreplay.LiteratureCloze()
    a = garak.attempt.Attempt(prompt="IS THIS BROKEN")
    a.outputs = ["", None]
    p._postprocess_hook(a)


def test_all_leakreplay_classes():
    """Test that all leakreplay probe classes can be instantiated and function correctly.
    
    This test verifies:
    1. All probe classes can be instantiated without errors
    2. The string replacement works properly (with special characters like %)
    3. Tag inheritance works correctly from parent classes
    """
    # Get all probe classes from leakreplay module
    leakreplay_classes = []
    for name, obj in inspect.getmembers(garak.probes.leakreplay):
        if (inspect.isclass(obj) and 
            obj.__module__ == 'garak.probes.leakreplay' and
            not name.endswith('Mixin') and   # Skip mixin classes
            issubclass(obj, garak.probes.Probe)):
            leakreplay_classes.append(obj)
    
    # Test that we found at least 8 classes (there should be more)
    assert len(leakreplay_classes) >= 8, "Not all leakreplay probe classes were found"
    
    # Initialize each class and test basic functionality
    for probe_class in leakreplay_classes:
        probe = None
        try:
            # Should initialize without errors
            probe = probe_class()
            
            # Test tag inheritance - check that all expected tags are inherited properly
            expected_tags = [
                "avid-effect:security:S0301",
                "owasp:llm10", 
                "owasp:llm06",
                "quality:Security:ExtractionInversion",
                "payload:leak:training"
            ]
            
            # Both Cloze and Complete classes should have all the same tags
            # Verify complete inheritance works as expected
            for tag in expected_tags:
                if "Complete" in probe_class.__name__ or "Cloze" in probe_class.__name__:
                    assert tag in probe.tags, f"{probe_class.__name__} is missing expected tag: {tag}"
                    
            # Also verify the total tag count to ensure no duplicates or extras
            expected_tag_count = len(expected_tags)
            if probe_class.__name__.endswith(('Cloze', 'ClozeFull', 'Complete', 'CompleteFull')):
                assert len(probe.tags) == expected_tag_count, \
                    f"{probe_class.__name__} has incorrect number of tags: {len(probe.tags)} instead of {expected_tag_count}"
                
            # Verify that prompts were created correctly (this tests the string replacement)
            assert len(probe.prompts) > 0, f"{probe_class.__name__} has no prompts"
            
            # Test template handling (specific to our string replacement fix)
            if hasattr(probe, '_attempt_prestore_hook'):
                # Create an attempt with a prompt containing % characters
                # This would fail if we were using % string formatting
                special_prompt = "Test with 100% special % characters"
                a = garak.attempt.Attempt(prompt=special_prompt)
                
                # Should not raise errors when % is in the prompt
                probe._attempt_prestore_hook(a, 0)
        except Exception as e:
            assert False, f"Failed to initialize or test {probe_class.__name__}: {e}"
            
        # Additional checks for specific class types
        if "Cloze" in probe_class.__name__:
            assert hasattr(probe, '_postprocess_hook'), "Cloze class missing _postprocess_hook"
            test_attempt = garak.attempt.Attempt(prompt="test")
            test_attempt.messages = [[{"content": "<name>Test</name>"}]]
            processed = probe._postprocess_hook(test_attempt)
            # Check that name tags are properly removed (part of postprocessing)
            assert "<name>" not in processed.messages[0][-1]["content"]

