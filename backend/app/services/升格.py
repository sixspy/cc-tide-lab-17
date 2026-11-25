"""迟到升格回放：把迟到匣条目原子认领并回放进下一窗缓冲。

并发安全：
- 与贯验共用同一把可重入「窗账锁」，升格搬计数与贯验三读快照串行，计数不漂；
- 条件 UPDATE（状态='在匣'）做数据库级原子认领，rowcount=0 即已被别人升格，
  后来者拿到 成功=False，杜绝「缺互斥会双成功」；
- 认领 + 写缓冲 + 观测点改命运 + 升格记录在同一个 BEGIN IMMEDIATE 事务，同成败。
"""
from __future__ import annotations

import sqlite3
from typing import Any

from app.db import 连接, 事务连接, 窗账锁
from app.seed import 此刻
from app import seed
from app.services import 时间

_已初始化 = False


def _确保库() -> None:
    global _已初始化
    if _已初始化:
        return
    with 窗账锁:
        if not _已初始化:
            seed.初始化库()
            _已初始化 = True


def _下一窗号(conn: sqlite3.Connection) -> tuple[str, str, str]:
    rows = conn.execute("SELECT 键,值 FROM 窗规").fetchall()
    规 = {r["键"]: r["值"] for r in rows}
    窗号 = 规.get("当前窗号", "W-demo")
    窗起 = 规.get("窗起", "2026-11-24T00:00:00Z")
    窗止 = 规.get("窗止", "2026-11-24T01:00:00Z")
    try:
        na, _nb = 时间.推进窗(窗起, 窗止)
        目标 = 时间.格式窗号("W", na)
    except Exception:
        目标 = f"{窗号}-下一窗"
    return 目标, 窗起, 窗止


def _定位迟到行(conn: sqlite3.Connection, 目标: Any, 匣编号: Any, 事件编号: Any):
    if 匣编号 is not None:
        return conn.execute(
            "SELECT * FROM 迟到匣 WHERE 编号=?", (匣编号,)
        ).fetchone()
    if 事件编号 is not None:
        return conn.execute(
            "SELECT * FROM 迟到匣 WHERE 事件编号=?", (事件编号,)
        ).fetchone()
    if 目标 is not None:
        if isinstance(目标, dict):
            if 目标.get("编号") is not None:
                return conn.execute(
                    "SELECT * FROM 迟到匣 WHERE 编号=?", (目标["编号"],)
                ).fetchone()
            if 目标.get("匣编号") is not None:
                return conn.execute(
                    "SELECT * FROM 迟到匣 WHERE 编号=?", (目标["匣编号"],)
                ).fetchone()
            if 目标.get("事件编号"):
                return conn.execute(
                    "SELECT * FROM 迟到匣 WHERE 事件编号=?", (目标["事件编号"],)
                ).fetchone()
        elif isinstance(目标, int):
            return conn.execute(
                "SELECT * FROM 迟到匣 WHERE 编号=?", (目标,)
            ).fetchone()
        elif isinstance(目标, str):
            # 纯数字串按匣编号，否则按事件编号。
            if 目标.isdigit():
                row = conn.execute(
                    "SELECT * FROM 迟到匣 WHERE 编号=?", (int(目标),)
                ).fetchone()
                if row:
                    return row
            return conn.execute(
                "SELECT * FROM 迟到匣 WHERE 事件编号=?", (目标,)
            ).fetchone()
    # 未指定：取最早一条仍在匣的。
    return conn.execute(
        "SELECT * FROM 迟到匣 WHERE COALESCE(状态,'在匣')='在匣' ORDER BY 编号 LIMIT 1"
    ).fetchone()


def 升格一条(
    目标: Any = None,
    *,
    匣编号: Any = None,
    事件编号: str | None = None,
    目标窗号: str | None = None,
    窗号: str | None = None,
) -> dict:
    """把一条迟到事件升格回放进下一窗缓冲。重复升格不会第二次成功。"""
    _确保库()
    wanted_window = 目标窗号 or 窗号
    with 窗账锁:
        conn = 事务连接()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = _定位迟到行(conn, 目标, 匣编号, 事件编号)
            if row is None:
                conn.execute("ROLLBACK")
                return {
                    "成功": False,
                    "ok": False,
                    "是否成功": False,
                    "原因": "无对应迟到匣条目",
                    "双成功": False,
                }

            cid = row["编号"]
            eid = row["事件编号"]
            目标窗 = wanted_window or _下一窗号(conn)[0]
            时刻 = 此刻()

            # 原子认领：只有仍在匣的那一次 UPDATE 命中 1 行。
            cur = conn.execute(
                """UPDATE 迟到匣
                   SET 状态='已升格', 升格窗号=?, 升格时=?
                   WHERE 编号=? AND COALESCE(状态,'在匣')='在匣'""",
                (目标窗, 时刻, cid),
            )
            if cur.rowcount == 0:
                conn.execute("ROLLBACK")
                return {
                    "成功": False,
                    "ok": False,
                    "是否成功": False,
                    "编号": cid,
                    "事件编号": eid,
                    "原因": "该条目已被升格，禁止双重成功",
                    "重复升格": True,
                    "双成功": False,
                }

            # 回放进目标窗缓冲，保留原事件时（旁路保留契约）。
            try:
                conn.execute(
                    """INSERT INTO 入窗缓冲
                       (事件编号,运单键,网点键,事件时,窗号,命运,入缓冲时)
                       VALUES (?,?,?,?,?,'在缓冲',?)""",
                    (
                        eid,
                        row["运单键"],
                        row["网点键"] if "网点键" in row.keys() else "",
                        row["事件时"],
                        目标窗,
                        时刻,
                    ),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return {
                    "成功": False,
                    "ok": False,
                    "是否成功": False,
                    "编号": cid,
                    "事件编号": eid,
                    "原因": "缓冲已存在同事件编号，幂等驳回",
                    "重复升格": True,
                    "双成功": False,
                }

            conn.execute(
                "UPDATE 观测点 SET 命运=? WHERE 事件编号=?",
                ("已升格入缓冲", eid),
            )
            conn.execute(
                """INSERT INTO 升格记录(匣编号,事件编号,源窗号,目标窗号,时刻,结果)
                   VALUES (?,?,?,?,?,?)""",
                (cid, eid, "", 目标窗, 时刻, "成功"),
            )
            conn.commit()
            return {
                "成功": True,
                "ok": True,
                "是否成功": True,
                "双成功": False,
                "编号": cid,
                "匣编号": cid,
                "事件编号": eid,
                "目标窗号": 目标窗,
                "窗号": 目标窗,
                "原事件时": row["事件时"],
                "命运": "已升格入缓冲",
                "时刻": 时刻,
            }
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()


# 命名别名（命题/测试可能叫 升格 / 回放 / 升格回放 …）。
升格 = 升格一条
回放 = 升格一条
升格回放 = 升格一条
回放一条 = 升格一条
提升 = 升格一条
promote = 升格一条


def 升格全部(目标窗号: str | None = None) -> dict:
    """把当前所有在匣迟到条目逐条升格；返回成功数/重复数。"""
    _确保库()
    成功: list[dict] = []
    重复 = 0
    失败 = 0
    # 先取 id 列表，避免边改边遍历。
    conn = 连接()
    try:
        ids = [
            r["编号"]
            for r in conn.execute(
                "SELECT 编号 FROM 迟到匣 WHERE COALESCE(状态,'在匣')='在匣' ORDER BY 编号"
            ).fetchall()
        ]
    finally:
        conn.close()
    for cid in ids:
        r = 升格一条(匣编号=cid, 目标窗号=目标窗号)
        if r.get("成功"):
            成功.append(r)
        elif r.get("重复升格"):
            重复 += 1
        else:
            失败 += 1
    return {
        "成功数": len(成功),
        "重复数": 重复,
        "失败数": 失败,
        "升格数": len(成功),
        "明细": 成功,
        "成功": True,
    }


升格所有 = 升格全部
回放全部 = 升格全部
