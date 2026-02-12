"""
Word count job — counts words, lines, and characters in a text file.

This is a real I/O job (reads from disk) as opposed to the simulated SleepJob.
It demonstrates that the system handles actual file processing, not just sleep().

Example payload:
    {"file_path": "/data/sample.txt"}

Example result:
    {
        "file_path": "/data/sample.txt",
        "word_count": 1024,
        "line_count": 42,
        "char_count": 5678
    }

The file_path refers to a path INSIDE the Docker container.
In docker-compose.yml, we mount ./sample_data → /data, so
"/data/sample.txt" maps to ./sample_data/sample.txt on your host machine.
"""

import os

from jobs.base import AbstractJobHandler


class WordCountJob(AbstractJobHandler):

    def run(self, payload: dict) -> dict:
        file_path = payload.get("file_path")
        if not file_path:
            raise ValueError("Missing 'file_path' in payload")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        words = len(content.split())
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        chars = len(content)

        return {
            "file_path": file_path,
            "word_count": words,
            "line_count": lines,
            "char_count": chars,
        }

    @property
    def job_type(self) -> str:
        return "word_count"
