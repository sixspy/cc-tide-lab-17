"""迟到/升格入口的兼容别名模块。

真实实现：读取在 app.services.目录，升格在 app.services.升格。
命题或测试若按领域名 ``app.services.迟到`` 导入，也能拿到同一套并发安全动作。
"""
from __future__ import annotations

from app.services.目录 import 迟到列表, 在匣迟到列表, 迟到全部列表
from app.services.升格 import (
    升格一条,
    升格,
    回放,
    升格回放,
    升格全部,
    promote,
)

__all__ = [
    "迟到列表",
    "在匣迟到列表",
    "迟到全部列表",
    "升格一条",
    "升格",
    "回放",
    "升格回放",
    "升格全部",
    "promote",
]
