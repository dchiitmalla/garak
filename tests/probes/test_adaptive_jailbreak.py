# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from unittest.mock import MagicMock, patch

import garak.attempt
from garak.probes.adaptive_jailbreak import SimpleAdaptiveJailbreak, AdaptiveJailbreakChain
from garak.generators.base import Generator


def test_simple_adaptive_jailbreak_initialization():
    """Test that SimpleAdaptiveJailbreak initializes with expected parameters."""
    probe = SimpleAdaptiveJailbreak()
    
    # Verify core attributes
    assert probe.lang == "en"
    assert "owasp:llm01" in probe.tags
    assert "payload:jailbreak" in probe.tags
    assert "bypass content safeguards through adaptive techniques" == probe.goal
    assert probe.active is True
    
    # Verify prompt structures exist
    assert len(probe.base_prompts) > 0
    assert len(probe.escalation_prompts) > 0
    assert len(probe.advanced_prompts) > 0
    assert len(probe.harmful_topics) > 0


def test_simple_adaptive_jailbreak_prompts():
    """Test that SimpleAdaptiveJailbreak generates expected prompts."""
    probe = SimpleAdaptiveJailbreak()
    prompts = probe.prompts()
    
    # Verify we get the expected number of prompts (one for each base template)
    assert len(prompts) == len(probe.base_prompts)
    
    # Verify all prompts are Attempt objects
    assert all(isinstance(p, garak.attempt.Attempt) for p in prompts)
    
    # Verify prompt notes contains expected fields
    for attempt in prompts:
        assert "harmful_topic" in attempt.notes
        assert "technique_level" in attempt.notes
        assert attempt.notes["technique_level"] == "base"
        assert "technique_index" in attempt.notes
        
        # Verify the harmful topic is included in the prompt
        assert attempt.notes["harmful_topic"] in attempt.prompt


def test_simple_adaptive_jailbreak_detected_refusal():
    """Test that the refusal detection function works correctly."""
    probe = SimpleAdaptiveJailbreak()
    
    # Test refusal detection on various response types
    assert probe._detected_refusal("I'm sorry, I cannot provide information on hacking.") is True
    assert probe._detected_refusal("I apologize, but I can't assist with that request.") is True
    assert probe._detected_refusal("That goes against my ethical guidelines.") is True
    
    # Test non-refusal responses
    assert probe._detected_refusal("Here's a detailed explanation of network security...") is False
    assert probe._detected_refusal("The key concepts to understand about cybersecurity include...") is False


def test_simple_adaptive_jailbreak_probe():
    """Test the adaptive probing behavior with a mock generator."""
    probe = SimpleAdaptiveJailbreak()
    
    # Create a mock generator that returns refusals for every prompt
    mock_generator = MagicMock(spec=Generator)
    
    def mock_generate(attempts):
        """Mock generate function that simulates model refusals."""
        for attempt in attempts:
            if "base" in attempt.notes.get("technique_level", ""):
                # Simulate refusal for base prompts
                attempt.response = "I'm sorry, I cannot provide information on harmful topics."
            elif "escalation" in attempt.notes.get("technique_level", ""):
                # Simulate refusal for escalation prompts
                attempt.response = "I apologize, but I still cannot assist with that request."
            else:
                # Simulate acceptance for advanced prompts
                attempt.response = "Here is information about the topic you requested..."
        return attempts
    
    mock_generator.generate.side_effect = mock_generate
    
    # Run the probe with the mock generator
    results = probe.probe(mock_generator)
    
    # Verify we get more attempts than just the base prompts (due to adaptive behavior)
    assert len(results) > len(probe.base_prompts)
    
    # Verify that we have escalation attempts
    escalation_attempts = [a for a in results if a.notes.get("technique_level") == "escalation"]
    assert len(escalation_attempts) > 0
    
    # Verify that we have advanced attempts (the final escalation)
    advanced_attempts = [a for a in results if a.notes.get("technique_level") == "advanced"]
    assert len(advanced_attempts) > 0


def test_adaptive_jailbreak_chain_initialization():
    """Test that AdaptiveJailbreakChain initializes with expected parameters."""
    probe = AdaptiveJailbreakChain()
    
    # Verify core attributes
    assert probe.lang == "en"
    assert "owasp:llm01" in probe.tags
    assert "payload:jailbreak" in probe.tags
    assert "bypass content safeguards through adaptive chained techniques" == probe.goal
    assert probe.active is False  # Should be disabled by default
    
    # Verify technique components exist
    assert "framing" in probe.technique_components
    assert "roleplay" in probe.technique_components
    assert "urgency" in probe.technique_components
    assert "authority" in probe.technique_components
    
    # Verify harmful requests exist
    assert len(probe.harmful_requests) > 0


def test_adaptive_jailbreak_chain_prompts():
    """Test that AdaptiveJailbreakChain generates expected prompts."""
    probe = AdaptiveJailbreakChain()
    prompts = probe.prompts()
    
    # Expected number of prompts: harmful_requests × technique_components
    expected_count = len(probe.harmful_requests) * len(probe.technique_components)
    assert len(prompts) == expected_count
    
    # Verify all prompts are Attempt objects
    assert all(isinstance(p, garak.attempt.Attempt) for p in prompts)
    
    # Verify prompt notes contains expected fields
    for attempt in prompts:
        assert "harmful_request" in attempt.notes
        assert attempt.notes["harmful_request"] in probe.harmful_requests
        assert "techniques_used" in attempt.notes
        assert "chain_depth" in attempt.notes
        assert attempt.notes["chain_depth"] == 1
