import os
import sqlite3
import threading
from pathlib import Path

数据目录 = Path(os.environ.get("数据目录", Path(__file__).resolve().parent.parent / "data"))
夹具目录 = Path(os.environ.get("夹具目录", Path(__file__).resolve().parent.parent.parent / "fixtures"))
库路径 = 数据目录 / "潮切.db"

# 窗账（缓冲 / 切片 / 迟到匣 / 贯验结论）进程内互斥闸。
# 贯验三读 + 写结论、迟到升格原子认领都走同一把可重入锁，
# 避免“升格与贯验并发计数漂移”和“缺互斥导致双重成功”。
窗账锁 = threading.RLock()


def 连接() -> sqlite3.Connection:
    数据目录.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(库路径, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    # 并发升格/贯验时遇到锁等待而不是立刻 database is locked。
    c.execute("PRAGMA busy_timeout = 8000")
    return c


def 事务连接() -> sqlite3.Connection:
    """显式事务连接：autocommit 模式，由调用方执行 BEGIN IMMEDIATE。

    这样三处读取与结论写入落在同一个一致性快照/写事务里，同成败。
    """
    c = 连接()
    c.isolation_level = None
    return c
