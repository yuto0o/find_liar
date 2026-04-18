import pytest

from feature.graphrag.extractor import extract_graph


def _make_stub(responses):
    calls = {"i": 0}

    def gen(prompt, **kwargs):
        i = calls["i"]
        calls["i"] += 1
        if i < len(responses):
            return responses[i]
        return responses[-1]

    return gen


def test_extract_graph_from_fenced_json(monkeypatch):
    resp = '```json\n{"edges": [{"source": "A", "target": "B", "relation": "supports"}]}\n```'
    monkeypatch.setattr("feature.llm.llama.generate", _make_stub([resp]))
    edges = extract_graph("dummy")
    assert len(edges) == 1
    e = edges[0]
    assert e.source == "A"
    assert e.target == "B"
    assert e.relation == "supports"


def test_extract_graph_from_brace_matching(monkeypatch):
    resp = (
        'prefix {"edges": [{"source":"A","target":"B","relation":"supports"}]} suffix'
    )
    monkeypatch.setattr("feature.llm.llama.generate", _make_stub([resp]))
    edges = extract_graph("x")
    assert len(edges) == 1
    assert edges[0].relation == "supports"


def test_extract_graph_convert_dict_mapping(monkeypatch):
    # Model returns a dict mapping like {"AとBの関係":"支持"}
    resp = '{"AとBの関係":"支持", "AとCの関係":"矛盾"}'
    monkeypatch.setattr("feature.llm.llama.generate", _make_stub([resp]))
    edges = extract_graph("x")
    assert len(edges) == 2
    rels = sorted([e.relation for e in edges])
    assert rels == ["contradicts", "supports"]


def test_extract_graph_repair_flow(monkeypatch):
    # First call returns garbled text, second (repair) returns valid JSON
    initial = "AとBの関係は？"
    repaired = '```json\n{"edges": [{"source": "A", "target": "B", "relation": "supports"}]}\n```'
    monkeypatch.setattr("feature.llm.llama.generate", _make_stub([initial, repaired]))
    edges = extract_graph("x")
    assert len(edges) == 1
    assert edges[0].relation == "supports"
