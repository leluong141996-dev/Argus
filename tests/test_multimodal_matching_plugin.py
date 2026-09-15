import json
from pathlib import Path

from plugins.multimodal_matching.ontology import ABSTAIN, normalize
from plugins.multimodal_matching import ontology as O
from plugins.multimodal_matching.plugin import MultimodalMatchingPlugin
from plugins.base import GenerationResult
from core.pipeline import Stage
from core.registry import get_plugin


def test_abstain_is_none():
    assert ABSTAIN is None


def test_normalize_trims_and_lowercases():
    assert normalize("  Red_Fox ") == "red_fox"
    assert normalize("RED_FOX") == "red_fox"


def test_normalize_coerces_non_strings():
    assert normalize(42) == "42"
    assert normalize(None) == "none"
