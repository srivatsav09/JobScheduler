"""Tests for the ThumbnailJob handler."""

import os
import tempfile
import pytest
from PIL import Image
from jobs.thumbnail import ThumbnailJob


@pytest.fixture
def sample_image():
    """Create a temporary 200x100 image."""
    img = Image.new("RGB", (200, 100), color=(255, 0, 0))
    path = os.path.join(tempfile.gettempdir(), "test_input.jpg")
    img.save(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def output_path():
    """Path for the generated thumbnail."""
    path = os.path.join(tempfile.gettempdir(), "test_thumb.jpg")
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_generates_thumbnail(sample_image, output_path):
    handler = ThumbnailJob()
    result = handler.run({
        "input_path": sample_image,
        "output_path": output_path,
        "width": 50,
        "height": 50,
    })

    assert os.path.exists(output_path)
    assert result["original_size"] == [200, 100]
    assert result["input_path"] == sample_image
    assert result["output_path"] == output_path

    # Verify the thumbnail was actually created and is smaller
    with Image.open(output_path) as thumb:
        assert thumb.size[0] <= 50
        assert thumb.size[1] <= 50


def test_auto_generates_output_path(sample_image):
    """When no output_path given, should create *_thumb.jpg."""
    handler = ThumbnailJob()
    result = handler.run({"input_path": sample_image})

    expected_output = sample_image.replace(".jpg", "_thumb.jpg")
    assert result["output_path"] == expected_output
    assert os.path.exists(expected_output)

    # Cleanup
    os.unlink(expected_output)


def test_missing_input_path():
    handler = ThumbnailJob()
    with pytest.raises(ValueError, match="Missing"):
        handler.run({})


def test_nonexistent_image():
    handler = ThumbnailJob()
    with pytest.raises(FileNotFoundError):
        handler.run({"input_path": "/nonexistent/image.jpg"})


def test_job_type():
    assert ThumbnailJob().job_type == "thumbnail"
