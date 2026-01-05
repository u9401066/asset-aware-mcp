"""
Test Fixtures for Asset-Aware MCP

Provides reusable fixtures for unit, integration, and E2E tests.
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown content for testing."""
    return """<!-- Page 1 -->

# Test Document Title

## Introduction

This is the introduction section.
It contains some important information about the topic.

<!-- Page 2 -->

## Methods

### Data Collection

We collected data from multiple sources.

| Column A | Column B | Column C |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |

<!-- Page 3 -->

## Results

The results show significant findings.

### Statistical Analysis

We performed t-tests on the data.

## Discussion

The findings suggest important implications.
"""


@pytest.fixture
def sample_manifest_dict() -> dict:
    """Sample manifest dictionary for testing."""
    return {
        "doc_id": "doc_test_abc123",
        "filename": "test.pdf",
        "title": "Test Document Title",
        "toc": ["Introduction", "Methods", "Results", "Discussion"],
        "assets": {
            "tables": [
                {
                    "id": "tab_1",
                    "page": 2,
                    "caption": "Table 1",
                    "preview": "Column A | Column B...",
                    "markdown": "| Column A | Column B | Column C |\n|----------|----------|----------|\n| Value 1  | Value 2  | Value 3  |",
                    "row_count": 2,
                    "col_count": 3,
                }
            ],
            "figures": [],
            "sections": [
                {"id": "sec_introduction", "title": "Introduction", "level": 1, "page": 1, "start_line": 5, "end_line": 10, "preview": "This is the introduction..."},
                {"id": "sec_methods", "title": "Methods", "level": 1, "page": 2, "start_line": 12, "end_line": 22, "preview": "We collected data..."},
            ],
        },
        "lightrag_entities": ["Term1", "Term2"],
        "page_count": 3,
        "markdown_path": "",
        "manifest_path": "",
    }
