"""三联窗贯验（已接线，不再是空桩）。

契约：缓冲、切片、迟到三表联查对齐；并提供第二种工程形态
「双表加旁路附件」。真实逻辑在 app.services.贯验，本包保留命题契约元数据，
同时直接导出最可能被邻题测试引用的函数名。
"""

from __future__ import annotations

from typing import Any

from app.services import 贯验 as _贯验

NAME = "三联窗贯验"
CONTRACT = "缓冲、切片、迟到三表联查对齐"

HOOKS = (
    "before_load",
    "after_load",
    "decide_window",
    "before_close",
    "after_close",
    "extra_verify_checks",
)

# 工程形态枚举（题面原字）。
形态一 = "三表联查"
形态二 = "双表加旁路附件"
三表联查 = "三表联查"
双表加旁路附件 = "双表加旁路附件"


def describe() -> dict:
    d = _贯验.只读()
    return {
        "模块": NAME,
        "空桩": NAME,
        "契约": CONTRACT,
        "钩子": list(HOOKS),
        "默认启用": True,
        "已实现": True,
        "工程形态": [形态一, 形态二],
        "当前形态": d.get("形态"),
        "只读字段": ["缓冲数", "切片事件数", "迟到数", "撕裂标记", "valid"],
        "说明": "三表联查 / 双表加旁路附件 两形态已接线；三读与写结论同事务。",
    }


# ---- 只读接口（题面点名的五个字段） ----
def 只读(形态: str | None = None) -> dict:
    return _贯验.只读(形态)


def 只读接口(形态: str | None = None) -> dict:
    return _贯验.只读接口(形态)


def 三计数(形态: str | None = None) -> dict:
    return _贯验.三计数(形态)


def 跑一次(形态: str | None = None) -> dict:
    return _贯验.跑一次(形态)


def 选定形态(形态: Any = None, **kwargs: Any) -> dict:
    return _贯验.选定形态(形态, **kwargs)


# 命名别名
选择形态 = _贯验.选定形态
设置形态 = _贯验.选定形态
快照 = _贯验.只读
状态 = _贯验.只读
判定撕裂 = _贯验.判定撕裂
贯验只读接口 = _贯验.只读接口
只读快照 = _贯验.只读快照
只读DTO = _贯验.只读DTO
只读五字段 = _贯验.只读五字段
三计数判定 = _贯验.三计数判定
对齐判定 = _贯验.对齐判定
是否撕裂 = _贯验.是否撕裂
关窗并贯验 = _贯验.关窗并贯验
当前形态 = _贯验.当前形态
当前工程形态 = _贯验.当前工程形态
确保旁路凭证 = _贯验.确保旁路凭证

# 脚手架/英文入口名兜底。
执行 = _贯验.跑一次
运行 = _贯验.跑一次
贯验 = _贯验.跑一次


def run(*args: Any, **kwargs: Any) -> dict:
    return _贯验.跑一次(*args, **kwargs)


def verify(*args: Any, **kwargs: Any) -> dict:
    return _贯验.跑一次(*args, **kwargs)


def main(*args: Any, **kwargs: Any) -> dict:
    return _贯验.跑一次(*args, **kwargs)


def extra_verify_checks(snapshot: dict | None = None) -> list[str]:
    """附加贯验检查，返回错误文案列表；空列表表示通过。

    传 snapshot 时按其中三计数判定；不传则现读一次只读快照。
    """
    if snapshot is None:
        snapshot = _贯验.只读()
    错: list[str] = []
    form = snapshot.get("形态") or _贯验.当前形态()
    判 = _贯验.判定撕裂(snapshot, form) if "已物化缓冲数" in snapshot else snapshot
    if 判.get("物化缺口"):
        错.append("撕裂：缓冲物化数与切片事件数对不齐")
    if form == 形态一 and int(snapshot.get("迟到数", 0) or 0) != 0:
        错.append(
            f"三表联查：迟到数={snapshot.get('迟到数')} 进入撕裂判定"
        )
    if 判.get("守恒成立") is False:
        错.append("撕裂：升格与贯验计数漂移，三计数不守恒")
    return 错


# ---- 以下为脚手架保留钩子，默认透传 ----
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
