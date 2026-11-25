"""列表与窗规读写。"""
from __future__ import annotations
from app.db import 连接


def 窗规() -> dict:
    conn = 连接()
    try:
        rows = conn.execute("SELECT 键,值 FROM 窗规").fetchall()
        return {r["键"]: r["值"] for r in rows}
    finally:
        conn.close()


def 改窗规(体: dict) -> dict:
    conn = 连接()
    try:
        for k, v in (体 or {}).items():
            conn.execute(
                "INSERT INTO 窗规(键,值) VALUES (?,?) ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
                (str(k), str(v)),
            )
        conn.commit()
        return 窗规()
    finally:
        conn.close()


def 网点列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 网点源 ORDER BY 源键").fetchall()]
    finally:
        conn.close()


def 观测列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 观测点 ORDER BY 事件时 DESC LIMIT 200").fetchall()]
    finally:
        conn.close()


def 缓冲列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 入窗缓冲 ORDER BY 事件时").fetchall()]
    finally:
        conn.close()


def 切片列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 窗切片账 ORDER BY 物化时 DESC LIMIT 200").fetchall()]
    finally:
        conn.close()


def 迟到列表(全部: bool = True, *, 在匣: bool = False, 仅在匣: bool = False) -> list[dict]:
    """迟到匣列表（保留行，升格只改「状态」不删行）。

    - 无参 / 全部=True：返回全部迟到行（基线契约，含 状态=已升格）；
    - 全部=False 或 在匣=True / 仅在匣=True：只返回仍在匣（未升格）条目。
    “匣内还剩多少”的计数口径以贯验只读 DTO 的「迟到数」为准。
    """
    active_only = bool(在匣 or 仅在匣 or 全部 is False)
    conn = 连接()
    try:
        if not active_only:
            sql = "SELECT * FROM 迟到匣 ORDER BY 编号 DESC LIMIT 200"
            return [dict(r) for r in conn.execute(sql).fetchall()]
        sql = (
            "SELECT * FROM 迟到匣 "
            "WHERE COALESCE(状态,'在匣')='在匣' ORDER BY 编号 DESC LIMIT 200"
        )
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def 迟到全部列表() -> list[dict]:
    return 迟到列表(全部=True)


def 在匣迟到列表() -> list[dict]:
    """仍在迟到匣（未升格）的条目。"""
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 迟到匣 WHERE COALESCE(状态,'在匣')='在匣' ORDER BY 编号 DESC LIMIT 200"
            ).fetchall()
        ]
    finally:
        conn.close()


def 旁路凭证列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 旁路凭证 ORDER BY 归档时 DESC LIMIT 200").fetchall()]
    finally:
        conn.close()


# 兼容命名：归档 / 旁路归档 / 归档凭证 都读到同一份凭证。
归档列表 = 旁路凭证列表
旁路归档列表 = 旁路凭证列表
归档凭证列表 = 旁路凭证列表


def 升格记录列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 升格记录 ORDER BY 编号 DESC LIMIT 100").fetchall()]
    finally:
        conn.close()


def 贯验列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 窗贯验 ORDER BY 编号 DESC LIMIT 50").fetchall()]
    finally:
        conn.close()


def 概览() -> dict:
    conn = 连接()
    try:
        迟到累计 = conn.execute("SELECT COUNT(*) AS c FROM 迟到匣").fetchone()["c"]
        在匣迟到 = conn.execute(
            "SELECT COUNT(*) AS c FROM 迟到匣 WHERE COALESCE(状态,'在匣')='在匣'"
        ).fetchone()["c"]
        return {
            "观测点": conn.execute("SELECT COUNT(*) AS c FROM 观测点").fetchone()["c"],
            "在缓冲": conn.execute("SELECT COUNT(*) AS c FROM 入窗缓冲 WHERE 命运='在缓冲'").fetchone()["c"],
            "窗切片": conn.execute("SELECT COUNT(*) AS c FROM 窗切片账").fetchone()["c"],
            # 旧键「迟到」保留全匣累计口径；在匣迟到为升格后的当前匣内数。
            "迟到": 迟到累计,
            "迟到累计": 迟到累计,
            "在匣迟到": 在匣迟到,
            "网点": conn.execute("SELECT COUNT(*) AS c FROM 网点源").fetchone()["c"],
            "贯验结论": conn.execute("SELECT COUNT(*) AS c FROM 窗贯验").fetchone()["c"],
            "旁路凭证": conn.execute("SELECT COUNT(*) AS c FROM 旁路凭证").fetchone()["c"],
            "窗规": 窗规(),
        }
    finally:
        conn.close()
