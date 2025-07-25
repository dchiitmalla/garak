# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Garak is an LLM vulnerability scanner and red-teaming framework - a security testing tool for language models. It probes for hallucination, data leakage, prompt injection, misinformation, toxicity generation, jailbreaks, and other security weaknesses in LLMs.

## Development Commands

### Testing
```bash
python3 -m pytest                    # Run all tests
python3 -m pytest tests/            # Run specific test directory
python3 -m pytest -v                # Verbose test output
python3 -m pytest --cov=garak       # Run tests with coverage
```

### Code Quality
```bash
python3 -m black .                  # Format code (line length: 88)
python3 -m pylint garak/            # Lint the main package
python3 -m pylint tests/            # Lint test files
```

### Installation and Development Setup
```bash
# Development install
python3 -m pip install -e .

# Install with optional dependencies
python3 -m pip install -e .[tests,lint,calibration,audio]

# Run garak 
python3 -m garak --help
python3 -m garak --list_probes
python3 -m garak --list_generators
```

## Architecture

### Core Components

1. **Probes** (`garak/probes/`) - Generate test interactions with LLMs to expose vulnerabilities
2. **Detectors** (`garak/detectors/`) - Analyze LLM outputs to identify failure modes  
3. **Generators** (`garak/generators/`) - Interface adapters for different LLM providers (OpenAI, HuggingFace, etc.)
4. **Harnesses** (`garak/harnesses/`) - Coordinate testing workflow between probes and detectors
5. **Evaluators** (`garak/evaluators/`) - Process and report assessment results
6. **Buffs** (`garak/buffs/`) - Transform prompts (encoding, paraphrasing, etc.)

### Plugin Architecture

Garak uses a plugin-based architecture where each component type has:
- Base classes in `base.py` files that define interfaces
- Plugin modules that inherit from base classes
- Automatic plugin discovery and loading via `_plugins.py`

### Configuration System

- Configuration hierarchy: plugin defaults < base config < site config < run config < CLI params
- YAML configuration files in `garak/configs/`
- Runtime configuration managed via `_config.py`
- Plugin-specific configs loaded dynamically

### Data and Resources

- Static test data in `garak/data/` (payloads, test sets, etc.)
- Runtime resources in `garak/resources/` (attack implementations, utilities)
- Plugin cache for performance optimization

## Key Development Patterns

### Creating New Plugins

1. Inherit from appropriate base class (`base.Probe`, `base.Detector`, etc.)
2. Override minimal required methods
3. Define `recommended_detectors` for probes
4. Place in appropriate module directory

### Testing Strategy

- Unit tests for individual plugins in `tests/[component]/`
- Integration tests that combine components
- Test generators use `test.Blank` and `test.Repeat` generators
- Mock external dependencies (API calls, file systems)

### Security Considerations

- All contributions must be for defensive security research
- Follow responsible disclosure for vulnerabilities
- Only include ethically appropriate test data
- Validate external inputs and API responses

## Important Files

- `garak/__main__.py` - CLI entry point
- `garak/cli.py` - Command line interface implementation  
- `garak/_plugins.py` - Plugin loading and discovery
- `garak/_config.py` - Configuration management
- `garak/attempt.py` - Core data structures for test attempts
- `pyproject.toml` - Build configuration and dependencies

## Dashboard Component

The `dashboard/` directory contains a Flask web application for visualizing garak results with authentication, job management, and report analysis capabilities.