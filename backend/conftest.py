"""Pytest 引导：把 backend 目录加入 sys.path。

无论从哪个工作目录、用 `pytest` 还是绝对路径收集用例，
都能正确 `from app... import ...`。
"""
import os
import sys

_BACKEND = os.path.dirname(os.path.abspath(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
