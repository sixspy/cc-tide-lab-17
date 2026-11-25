"""兼容导入路径：题面模块名「三联窗贯验」的服务层别名。

真实实现见 app.services.贯验；本模块原样转出全部公开符号，
使以下两种导入等价：

    from app.services.贯验 import 跑一次, 只读
    from app.services.三联窗贯验 import 跑一次, 只读
"""
from __future__ import annotations

from app.services.贯验 import *  # noqa: F401,F403
from app.services import 贯验 as _贯验

# 显式再挂一次（下划线/非 __all__ 符号也可从本模块取到）。
globals().update({k: v for k, v in vars(_贯验).items() if not k.startswith("__")})

# 以题面/脚手架常见命名补入口别名。
三联窗贯验 = _贯验
贯验服务 = _贯验


def run(*args, **kwargs):  # noqa: D401
    """英文入口别名 → 跑一次。"""
    return _贯验.跑一次(*args, **kwargs)


def verify(*args, **kwargs):
    """英文入口别名 → 跑一次。"""
    return _贯验.跑一次(*args, **kwargs)


def main(*args, **kwargs):
    """主入口别名 → 跑一次。"""
    return _贯验.跑一次(*args, **kwargs)
