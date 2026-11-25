"""旁路归档凭证的兼容别名模块。真实读取在 app.services.目录。"""
from __future__ import annotations

from app.services.目录 import (
    旁路凭证列表,
    归档列表,
    旁路归档列表,
    归档凭证列表,
)
from app.services.贯验 import 确保旁路凭证

写凭证 = 确保旁路凭证
归档 = 确保旁路凭证

__all__ = [
    "旁路凭证列表",
    "归档列表",
    "旁路归档列表",
    "归档凭证列表",
    "确保旁路凭证",
    "写凭证",
    "归档",
]
