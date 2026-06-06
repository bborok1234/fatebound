"""세이브 보안/견고성 — 라운드트립 + 크래프티드 세이브 안전 거부(crash/RCE 없음)."""
import json
import os
import importlib


def _persist(tmp_path):
    os.environ["FATEBOUND_SAVE_DIR"] = str(tmp_path)
    import fatebound.persistence as P
    importlib.reload(P)
    return P


def test_roundtrip(tmp_path):
    P = _persist(tmp_path)
    from fatebound.engine.session import GameSession
    s = GameSession.new_game("천기노조", "poison")
    s.level = 13; s.gold = 777
    P.save(s)
    loaded = P.load()
    assert loaded is not None
    assert loaded.level == 13 and loaded.gold == 777 and loaded.build == "poison"


def test_malformed_json_returns_none(tmp_path):
    P = _persist(tmp_path)
    (tmp_path / "default.json").write_text("{not valid json,,,", encoding="utf-8")
    assert P.load() is None        # 크래시 대신 None


def test_non_dict_save_rejected(tmp_path):
    P = _persist(tmp_path)
    (tmp_path / "default.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert P.load() is None        # 비-dict 거부


def test_future_version_rejected(tmp_path):
    P = _persist(tmp_path)
    (tmp_path / "default.json").write_text(json.dumps({"v": 999, "name": "x"}), encoding="utf-8")
    assert P.load() is None        # 미래/미상 스키마 거부


def test_crafted_wrong_types_no_crash(tmp_path):
    P = _persist(tmp_path)
    bad = {"v": 1, "name": {"nested": "evil"}, "build": ["list"], "level": "NaN", "bag": "notalist"}
    (tmp_path / "default.json").write_text(json.dumps(bad), encoding="utf-8")
    P.load()                       # None 또는 객체 — 예외 전파만 없으면 OK
