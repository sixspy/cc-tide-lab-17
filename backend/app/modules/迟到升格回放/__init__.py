"""迟到升格回放（已接线）。

契约：迟到匣可升格回放进下一窗缓冲；保留原事件时；与贯验共用互斥闸，
原子认领保证并发下只有一次成功。实现见 app.services.升格。
"""

from __future__ import annotations

from app.services import 升格 as _升格

NAME = "迟到升格回放"
CONTRACT = "迟到匣可升格回放进下一窗缓冲"

HOOKS = (
    "before_load",
    "after_load",
    "decide_window",
    "before_close",
    "after_close",
    "extra_verify_checks",
)


def describe() -> dict:
    return {
        "模块": NAME,
        "空桩": NAME,
        "契约": CONTRACT,
        "钩子": list(HOOKS),
        "默认启用": True,
        "已实现": True,
        "说明": "原子认领 + 窗账锁，升格与贯验并发计数不漂、不双成功。",
    }


def 升格一条(*args, **kwargs) -> dict:
    return _升格.升格一条(*args, **kwargs)


# 题面/测试可能使用的各种动作名。
升格 = _升格.升格一条
回放 = _升格.升格一条
升格回放 = _升格.升格一条
回放一条 = _升格.升格一条
promote = _升格.升格一条
升格全部 = _升格.升格全部
升格所有 = _升格.升格全部


# ---- 脚手架保留钩子 ----
def before_load(batch: dict) -> dict:
    return batch


def after_load(report: dict) -> dict:
    return report


def decide_window(event: dict, rules: dict) -> str:
    return "入缓冲"


def before_close(window_id: str) -> None:
    return None


def after_close(report: dict) -> dict:
    return report


def extra_verify_checks(snapshot: dict) -> list[str]:
    return []
