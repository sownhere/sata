"""Unit tests for bundled demo-mode samples."""

import pytest

from src.tools.demo_catalog import get_demo_sample, list_demo_samples
from src.tools.spec_parser import parse_openapi_spec


def test_demo_catalog_contains_required_samples_in_stable_order():
    samples = list_demo_samples()
    assert [sample["name"] for sample in samples] == [
        "PetStore",
        "ReqRes",
        "JSONPlaceholder",
    ]


def test_demo_catalog_samples_include_parseable_bundled_specs():
    for sample in list_demo_samples():
        model = parse_openapi_spec(sample["raw_spec"])
        assert model["title"]
        assert model["endpoints"]


def test_get_demo_sample_rejects_unknown_id():
    with pytest.raises(KeyError):
        get_demo_sample("unknown-sample")


def test_demo_samples_expose_source_url_not_spec_url():
    """Guard against regressing back to the `spec_url` name.

    The URLs point at human-facing landing pages (not openapi fetch endpoints),
    so they are labelled as `source_url` and only surfaced as a caption.
    """
    for sample in list_demo_samples():
        assert "source_url" in sample
        assert "spec_url" not in sample
