"""分析结果解析单元测试（不依赖引擎）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.analysis import build_view


def test_build_view_black():
    res = {
        "rootInfo": {"currentPlayer": "B", "winrate": 0.65, "scoreLead": 3.2},
        "moveInfos": [
            {"move": "Q16", "winrate": 0.7, "visits": 120, "scoreLead": 5.0},
            {"move": "D4", "winrate": 0.6, "visits": 80, "scoreLead": 1.0},
        ],
    }
    v = build_view(res, 19)
    assert v["best"]["row"] == 3 and v["best"]["col"] == 15
    assert v["top"][0]["visits"] == 120
    assert abs(v["winrate"] - 0.65) < 1e-9
    assert abs(v["score_lead"] - 3.2) < 1e-9


def test_build_view_white_current_player():
    """KataGo 的 winrate/scoreLead 以当前行棋方为视角，白方回合直接透传。"""
    res = {
        "rootInfo": {"currentPlayer": "W", "winrate": 0.6, "scoreLead": 2.0},
        "moveInfos": [{"move": "Q16", "winrate": 0.7, "visits": 100, "scoreLead": 5.0}],
    }
    v = build_view(res, 19)
    assert abs(v["winrate"] - 0.6) < 1e-9
    assert abs(v["score_lead"] - 2.0) < 1e-9
    assert abs(v["top"][0]["winrate"] - 0.7) < 1e-9

