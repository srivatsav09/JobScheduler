"""Tests for the WordCountJob handler."""

import os
import tempfile
import pytest
from jobs.word_count import WordCountJob


@pytest.fixture
def sample_file():
    """Create a temporary text file with known content."""
    content = "hello world\nfoo bar baz\n"
    # 5 words, 2 lines, 24 characters
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


def test_counts_words_lines_chars(sample_file):
    handler = WordCountJob()
    result = handler.run({"file_path": sample_file})

    assert result["word_count"] == 5
    assert result["line_count"] == 2
    assert result["char_count"] == 24
    assert result["file_path"] == sample_file


def test_missing_file_path():
    handler = WordCountJob()
    with pytest.raises(ValueError, match="Missing"):
        handler.run({})


def test_nonexistent_file():
    handler = WordCountJob()
    with pytest.raises(FileNotFoundError):
        handler.run({"file_path": "/nonexistent/file.txt"})


def test_empty_file():
    """Empty file should have 0 words, 0 lines, 0 chars."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        path = f.name
    try:
        handler = WordCountJob()
        result = handler.run({"file_path": path})
        assert result["word_count"] == 0
        assert result["char_count"] == 0
    finally:
        os.unlink(path)


def test_job_type():
    assert WordCountJob().job_type == "word_count"
