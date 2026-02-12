"""
Thumbnail generation job — resizes an image using Pillow.

This is the most tangible job type: you submit it, and a new file
appears on disk. Great for demos — "look, it actually processed this image."

Example payload:
    {
        "input_path": "/data/sample.jpg",
        "output_path": "/data/sample_thumb.jpg",
        "width": 128,
        "height": 128
    }

Example result:
    {
        "input_path": "/data/sample.jpg",
        "output_path": "/data/sample_thumb.jpg",
        "original_size": [1920, 1080],
        "thumbnail_size": [128, 72]
    }

Note: Pillow's thumbnail() preserves aspect ratio. If the image is
1920x1080 and you request 128x128, the result is 128x72 (not stretched).
"""

import os

from PIL import Image

from jobs.base import AbstractJobHandler


class ThumbnailJob(AbstractJobHandler):

    DEFAULT_SIZE = (128, 128)

    def run(self, payload: dict) -> dict:
        input_path = payload.get("input_path")
        if not input_path:
            raise ValueError("Missing 'input_path' in payload")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Image not found: {input_path}")

        output_path = payload.get("output_path")
        if not output_path:
            # Auto-generate: sample.jpg → sample_thumb.jpg
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_thumb{ext}"

        width = payload.get("width", self.DEFAULT_SIZE[0])
        height = payload.get("height", self.DEFAULT_SIZE[1])

        with Image.open(input_path) as img:
            original_size = img.size
            img.thumbnail((width, height))
            img.save(output_path)

        return {
            "input_path": input_path,
            "output_path": output_path,
            "original_size": list(original_size),
            "thumbnail_size": [width, height],
        }

    @property
    def job_type(self) -> str:
        return "thumbnail"
