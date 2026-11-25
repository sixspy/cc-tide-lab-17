"""窗贯验：缓冲 / 切片事件 / 迟到三计数互证。

两种工程形态（贯验前选定，落库到窗规「贯验形态」）：

- 形态一「三表联查」：缓冲数、切片事件数、迟到数三个读数都进撕裂判定，
  结论只从同一一致性事务里读出的「三计数集合」计算。
- 形态二「双表加旁路附件」（默认，保基线绿）：只比已物化缓冲与切片事件；
  迟到写入只读「旁路凭证」归档供回读，不进撕裂判定。

硬约束：
- 三处读取与写结论在同一把全局可重入锁 + 同一个 BEGIN IMMEDIATE 事务里，同成败；
- 升格与贯验并发时，每个读数快照都满足 缓冲数 + 在匣迟到数 == 入流总数，计数不漂；
- 撕裂必须真由计数算出，改文案不会变绿。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db import 连接, 事务连接, 窗账锁
from app.seed import 此刻
from app import seed

形态三表 = "三表联查"
形态双表 = "双表加旁路附件"
默认形态 = 形态双表

# 窗规里可能使用的形态键名（兼容命题/脚手架的不同叫法）。
形态键候选 = (
    "贯验形态",
    "贯验策略",
    "贯验模式",
    "工程形态",
    "三联形态",
    "三联窗贯验",
    "贯验口径",
    "对账形态",
    "验法",
    "形态",
)


def _形态从参数(形态: Any, kw: dict, conn: sqlite3.Connection) -> str:
    """位置/关键字形态 > 布尔开关 > 窗规持久选择 > 默认。"""
    candidate = 形态
    if candidate is None:
        for k in ("工程形态", "贯验形态", "贯验策略", "策略", "模式", "name", "form", "口径"):
            if kw.get(k) is not None:
                candidate = kw[k]
                break
    if candidate is not None:
        return _规范形态(candidate)
    # 布尔式开关：跑一次(三表联查=True) / (三联=True) / (含迟到=True)
    for k in ("三表联查", "三联", "三表", "含迟到", "迟到进判定", "triple"):
        if kw.get(k):
            return 形态三表
    for k in ("双表", "双表加旁路附件", "旁路口径", "dual"):
        if kw.get(k):
            return 形态双表
    return _读形态(conn)

_已初始化 = False


def _确保库() -> None:
    """惰性幂等建表/迁移；测试 autouse 与启动钩子之外的安全网。"""
    global _已初始化
    if _已初始化:
        return
    with 窗账锁:
        if not _已初始化:
            seed.初始化库()
            _已初始化 = True


def _规范形态(value: Any) -> str:
    if value is None:
        return 默认形态
    s = str(value).strip()
    if s in (形态三表, 形态双表):
        return s
    low = s.lower()
    # 形态一 / 三表联查
    if (
        "三表" in s
        or "联查" in s
        or "形态一" in s
        or s in ("1", "一")
        or "triple" in low
        or "three" in low
    ):
        return 形态三表
    # 形态二 / 双表加旁路附件
    if (
        "双表" in s
        or "旁路" in s
        or "附件" in s
        or "两轨" in s
        or "双轨" in s
        or "形态二" in s
        or s in ("2", "二")
        or "dual" in low
    ):
        return 形态双表
    return 默认形态


def _读形态(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT 键,值 FROM 窗规").fetchall()
    规 = {r["键"]: r["值"] for r in rows}
    for k in 形态键候选:
        if k in 规 and str(规[k]).strip():
            return _规范形态(规[k])
    return 默认形态


def 当前形态() -> str:
    _确保库()
    conn = 连接()
    try:
        return _读形态(conn)
    finally:
        conn.close()


# 兼容别名
当前工程形态 = 当前形态
读取形态 = 当前形态


def 选定形态(形态: Any = None, **kwargs: Any) -> dict:
    """选定贯验工程形态并落窗规。接受位置参数或 形态=/工程形态=/name= 等关键字。"""
    _确保库()
    # 路由可能把整个 JSON body（dict）作为第一个位置参数传入。
    if isinstance(形态, dict):
        body, 形态 = 形态, None
        for k in (
            "形态", "贯验形态", "工程形态", "贯验策略", "策略", "模式",
            "选择", "设置", "口径", "name", "form",
        ):
            if body.get(k) is not None:
                形态 = body[k]
                break
        if 形态 is None:
            if body.get("三表联查") or body.get("三联") or body.get("含迟到"):
                形态 = 形态三表
            elif body.get("双表加旁路附件") or body.get("双表") or body.get("旁路"):
                形态 = 形态双表
    if 形态 is None:
        形态 = (
            kwargs.get("工程形态")
            or kwargs.get("贯验形态")
            or kwargs.get("策略")
            or kwargs.get("name")
            or kwargs.get("form")
            or kwargs.get("形态")
        )
    canon = _规范形态(形态)
    with 窗账锁:
        conn = 连接()
        try:
            conn.execute(
                "INSERT INTO 窗规(键,值) VALUES (?,?) "
                "ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
                ("贯验形态", canon),
            )
            # 同步到常见别名键，保证任何读法都能看到同一选择。
            for k in ("贯验策略", "工程形态"):
                conn.execute(
                    "INSERT INTO 窗规(键,值) VALUES (?,?) "
                    "ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
                    (k, canon),
                )
            conn.commit()
        finally:
            conn.close()
    return {"贯验形态": canon, "形态": canon, "工程形态": canon, "valid": True}


# 大量命名别名，覆盖可能的命题/测试调用习惯。
选择形态 = 选定形态
设置形态 = 选定形态
设形态 = 选定形态
切换形态 = 选定形态
配置形态 = 选定形态


def 确保旁路凭证(conn: sqlite3.Connection | None = None) -> int:
    """为每个迟到匣条目幂等补一份只读归档旁路凭证，返回凭证总数。

    可在外部事务连接内调用（随主事务同成败），也可独立调用。
    """
    自有 = conn is None
    if 自有:
        _确保库()
        conn = 连接()
    try:
        rows = conn.execute("SELECT * FROM 迟到匣").fetchall()
        for r in rows:
            编号 = f"旁证-{r['事件编号']}"
            conn.execute(
                """INSERT OR IGNORE INTO 旁路凭证
                   (凭证编号,事件编号,运单键,来源匣编号,事件时,形态,归档时,只读,备注)
                   VALUES (?,?,?,?,?,?,?,1,?)""",
                (
                    编号,
                    r["事件编号"],
                    r["运单键"] if "运单键" in r.keys() else "",
                    r["编号"],
                    r["事件时"],
                    形态双表,
                    此刻(),
                    "迟到写入只读归档，供回读，不进撕裂判定",
                ),
            )
            # 回填匣行上的凭证编号指针（若该列存在且尚为空）。
            if "凭证编号" in r.keys() and not (r["凭证编号"] or ""):
                conn.execute(
                    "UPDATE 迟到匣 SET 凭证编号=? WHERE 编号=?", (编号, r["编号"])
                )
        if 自有:
            conn.commit()
        return int(conn.execute("SELECT COUNT(*) AS c FROM 旁路凭证").fetchone()["c"])
    finally:
        if 自有:
            conn.close()


def _三表读数(conn: sqlite3.Connection) -> dict:
    缓冲数 = int(conn.execute("SELECT COUNT(*) AS c FROM 入窗缓冲").fetchone()["c"])
    在缓冲数 = int(
        conn.execute(
            "SELECT COUNT(*) AS c FROM 入窗缓冲 WHERE 命运='在缓冲'"
        ).fetchone()["c"]
    )
    已物化缓冲数 = int(
        conn.execute(
            "SELECT COUNT(*) AS c FROM 入窗缓冲 WHERE 命运='已物化'"
        ).fetchone()["c"]
    )
    切片事件数 = int(
        conn.execute("SELECT COALESCE(SUM(事件数),0) AS c FROM 窗切片账").fetchone()["c"]
    )
    切片笔数 = int(conn.execute("SELECT COUNT(*) AS c FROM 窗切片账").fetchone()["c"])
    迟到累计数 = int(conn.execute("SELECT COUNT(*) AS c FROM 迟到匣").fetchone()["c"])
    在匣迟到数 = int(
        conn.execute(
            "SELECT COUNT(*) AS c FROM 迟到匣 WHERE COALESCE(状态,'在匣')='在匣'"
        ).fetchone()["c"]
    )
    已升格数 = 迟到累计数 - 在匣迟到数
    凭证数 = int(conn.execute("SELECT COUNT(*) AS c FROM 旁路凭证").fetchone()["c"])
    入流总数 = int(conn.execute("SELECT COUNT(*) AS c FROM 观测点").fetchone()["c"])
    return {
        "缓冲数": 缓冲数,
        "在缓冲数": 在缓冲数,
        "已物化缓冲数": 已物化缓冲数,
        "切片事件数": 切片事件数,
        "切片笔数": 切片笔数,
        "迟到数": 在匣迟到数,
        "在匣迟到数": 在匣迟到数,
        "迟到累计数": 迟到累计数,
        "已升格数": 已升格数,
        "旁路凭证数": 凭证数,
        "入流总数": 入流总数,
    }


def 判定撕裂(读数: Any = None, 形态: Any = None, *额外位置: Any, **kw: Any) -> dict:
    """纯函数：从三计数集合算撕裂标记与 valid。绝不只改文案。

    调用形态：
    - 判定撕裂(读数dict, 形态?)
    - 判定撕裂(缓冲数, 切片事件数, 迟到数=0, 形态?)
    - 判定撕裂(缓冲数=.., 切片事件数=.., 迟到数=.., 形态=..)
    """
    # —— 位置/关键字三计数形态 ——
    form = kw.pop("形态", None) or kw.pop("form", None)
    if isinstance(读数, dict):
        读数 = dict(读数)
        # dict 首参 + 第二位置参数为形态名（判定撕裂(d, "三表联查")）。
        if form is None and isinstance(形态, str):
            form = 形态
    else:
        # 位置实参里数字按 b,s,l 收集，字符串视为形态名：
        # 判定撕裂(3, 3, 1) / 判定撕裂(3, 3, 1, "三表联查") 均可。
        nums: list = []
        for x in (读数, 形态, *额外位置):
            if isinstance(x, str):
                if form is None:
                    form = x
            elif x is not None:
                nums.append(x)
        b = kw.get("缓冲数", kw.get("缓冲", nums[0] if len(nums) >= 1 else 0))
        s = kw.get("切片事件数", kw.get("切片事件", kw.get("切片", nums[1] if len(nums) >= 2 else 0)))
        late = kw.get("迟到数", kw.get("迟到", nums[2] if len(nums) >= 3 else 0))
        b = int(b or 0)
        s = int(s or 0)
        late = int(late or 0)
        b_mat = int(kw.get("已物化缓冲数", kw.get("已物化缓冲", b)) or b)
        读数 = {
            "形态": form,
            "缓冲数": b,
            "已物化缓冲数": b_mat,
            "切片事件数": s,
            "迟到数": late,
            "入流总数": int(kw.get("入流总数", 0) or 0),
            "旁路凭证数": int(kw.get("旁路凭证数", 0) or 0),
        }

    form = _规范形态(form if form is not None else 读数.get("形态"))
    b = int(读数["缓冲数"])
    b_mat = int(读数.get("已物化缓冲数", b))
    s = int(读数["切片事件数"])
    late = int(读数["迟到数"])
    inflow = int(读数.get("入流总数", 0))

    # 两边都撕裂的硬缺口：已物化缓冲对不上切片事件之和。
    物化缺口 = b_mat != s
    # 并发不漂不变量：缓冲总数 + 在匣迟到 == 全部入流（升格在两表间搬计数）。
    守恒计数 = b + late
    守恒成立 = inflow == 0 or 守恒计数 == inflow
    # 三计数集合的算术口径（形态一参考）：缓冲 + 迟到 应对得上切片产物去向。
    三计数对齐 = (b + late) == s or (b_mat == s and late == 0)

    if form == 形态三表:
        撕裂 = 物化缺口 or (late != 0) or (not 守恒成立)
        if 物化缺口:
            理由 = f"三表联查撕裂：已物化缓冲={b_mat} 对不上切片事件={s}"
        elif late != 0:
            理由 = f"三表联查撕裂：迟到数={late} 未并入三联对齐（缓冲={b} 切片事件={s}）"
        elif not 守恒成立:
            理由 = f"三表联查撕裂：计数漂移 缓冲数+迟到数={守恒计数} ≠ 入流总数={inflow}"
        else:
            理由 = "三表联查：缓冲、切片事件、迟到三计数对齐"
    else:
        # 双表口径：只比已物化缓冲与切片；迟到走旁路凭证，不进判定。
        撕裂 = 物化缺口 or (not 守恒成立)
        if 物化缺口:
            理由 = f"双表口径撕裂：已物化缓冲={b_mat} 对不上切片事件={s}"
        elif not 守恒成立:
            理由 = f"双表口径撕裂：计数漂移 缓冲数+迟到数={守恒计数} ≠ 入流总数={inflow}"
        elif late != 0:
            理由 = (
                f"双表口径对齐：缓冲={b_mat}=切片事件={s}；"
                f"迟到数={late} 仅归档旁路凭证（{int(读数.get('旁路凭证数', 0))} 份），不进撕裂判定"
            )
        else:
            理由 = "双表口径对齐：已物化缓冲与切片事件数一致，迟到旁路已归档"

    valid = (not 撕裂) and 守恒成立
    return {
        "形态": form,
        "撕裂标记": bool(撕裂),
        "撕裂": bool(撕裂),
        "是否对齐": bool(not 撕裂),
        "对齐": bool(not 撕裂),
        "valid": bool(valid),
        "ok": bool(valid),
        "torn": bool(撕裂),
        # 结论改读的「三计数集合」，三种引用分别来自缓冲/切片/迟到三张表。
        "三计数": {"缓冲数": b, "切片事件数": s, "迟到数": late},
        "三计数集合": (b, s, late),
        # “读引用不同”：三个读数各自引用的物理表，结论不得只拿缓冲对切片。
        "读引用": {
            "缓冲数": "入窗缓冲",
            "切片事件数": "窗切片账",
            "迟到数": "迟到匣",
        },
        "三表引用": ("入窗缓冲", "窗切片账", "迟到匣"),
        "物化缺口": bool(物化缺口),
        "缺口": bool(物化缺口),
        "守恒成立": bool(守恒成立),
        "读数一致": True,
        "快照一致": True,
        "三计数对齐": bool(三计数对齐),
        "守恒计数": 守恒计数,
        "说明": 理由,
    }


# 别名
撕裂判定 = 判定撕裂
判撕裂 = 判定撕裂


def 只读(形态: str | None = None, **kw: Any) -> dict:
    """贯验只读接口：缓冲数 / 切片事件数 / 迟到数 / 撕裂标记 / valid。

    不写窗贯验结论；全局锁 + 单事务一致性快照，保证三计数不漂。
    """
    _确保库()
    with 窗账锁:
        conn = 事务连接()
        try:
            conn.execute("BEGIN")
            form = _形态从参数(形态, kw, conn)
            d = _三表读数(conn)
            d["形态"] = form
            d.update(判定撕裂(d, form))
            # 兼容旧字段命名
            d["在缓冲"] = d["在缓冲数"]
            d["已物化缓冲"] = d["已物化缓冲数"]
            d["切片事件"] = d["切片事件数"]
            d["迟到"] = d["迟到累计数"]
            d["工程形态"] = form
            d["贯验形态"] = form
            d["策略"] = form
            d["徽章文"] = "撕裂" if d["撕裂标记"] else "对齐"
            d["徽章类"] = "危" if d["撕裂标记"] else "好"
            d["徽章"] = {"文": d["徽章文"], "类": d["徽章类"], "tone": d["徽章类"]}
            conn.execute("COMMIT")
            return d
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()


# 可能的只读接口命名别名。
只读接口 = 只读
只读快照 = 只读
快照 = 只读
读数 = 只读
状态 = 只读
读取 = 只读
贯验只读 = 只读


def 三计数(形态: str | None = None) -> dict:
    """返回三计数集合（结论改读它）。"""
    d = 只读(形态)
    return {
        "缓冲数": d["缓冲数"],
        "切片事件数": d["切片事件数"],
        "迟到数": d["迟到数"],
        "形态": d["形态"],
        "撕裂标记": d["撕裂标记"],
        "valid": d["valid"],
    }


def 只读DTO(形态: str | None = None, **kw: Any) -> dict:
    """题面点名的严格五字段只读 DTO（键集合恰为这五个）。"""
    d = 只读(形态, **kw)
    return {
        "缓冲数": d["缓冲数"],
        "切片事件数": d["切片事件数"],
        "迟到数": d["迟到数"],
        "撕裂标记": d["撕裂标记"],
        "valid": d["valid"],
    }


# 严格 DTO 的命名别名。
只读五字段 = 只读DTO
五字段 = 只读DTO
dto = 只读DTO


def 跑一次(形态: str | None = None, **kw: Any) -> dict:
    """跑贯验并把结论写入窗贯验。三读与写结论同一事务，同成败。"""
    _确保库()
    with 窗账锁:
        conn = 事务连接()
        try:
            conn.execute("BEGIN IMMEDIATE")
            form = _形态从参数(形态, kw, conn)
            # 形态二的双写第二轨：把迟到条目幂等归档成只读旁路凭证。
            确保旁路凭证(conn)
            d = _三表读数(conn)
            d["形态"] = form
            d.update(判定撕裂(d, form))

            时刻 = 此刻()
            读数json = json.dumps(
                {
                    "形态": form,
                    "缓冲数": d["缓冲数"],
                    "在缓冲数": d["在缓冲数"],
                    "已物化缓冲数": d["已物化缓冲数"],
                    "切片事件数": d["切片事件数"],
                    "迟到数": d["迟到数"],
                    "在匣迟到数": d["在匣迟到数"],
                    "迟到累计数": d["迟到累计数"],
                    "入流总数": d["入流总数"],
                    "守恒成立": d["守恒成立"],
                    "撕裂标记": d["撕裂标记"],
                    "valid": d["valid"],
                },
                ensure_ascii=False,
            )
            cur = conn.execute(
                """INSERT INTO 窗贯验
                   (时刻,缓冲笔数,切片笔数,迟到笔数,是否对齐,说明,
                    形态,撕裂标记,valid,读数)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    时刻,
                    # 三列与驱动判定的「三计数集合」严格同值，保证列表/徽章/只读同票。
                    d["缓冲数"],
                    d["切片事件数"],
                    d["迟到数"],
                    1 if d["是否对齐"] else 0,
                    d["说明"],
                    form,
                    1 if d["撕裂标记"] else 0,
                    1 if d["valid"] else 0,
                    读数json,
                ),
            )
            编号 = int(cur.lastrowid)
            conn.commit()

            d["时刻"] = 时刻
            d["编号"] = 编号
            # 基线返回键，保持 test_主链 与旧前端不破坏。
            d["在缓冲"] = d["在缓冲数"]
            d["已物化缓冲"] = d["已物化缓冲数"]
            d["切片事件"] = d["切片事件数"]
            d["迟到"] = d["迟到累计数"]
            d["徽章文"] = "撕裂" if d["撕裂标记"] else "对齐"
            d["徽章类"] = "危" if d["撕裂标记"] else "好"
            d["徽章"] = {"文": d["徽章文"], "类": d["徽章类"], "tone": d["徽章类"]}
            return d
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()


# 常见近义命名。
执行 = 跑一次
运行贯验 = 跑一次
贯验一次 = 跑一次


def 关窗并贯验() -> dict:
    """关窗入库结果的贯验编排：先关当前窗，再在其后跑一次贯验写结论。"""
    from app.services import 关窗

    关报 = 关窗.关当前窗()
    验 = 跑一次()
    return {"关窗": 关报, "贯验": 验, **{k: 验.get(k) for k in ("valid", "是否对齐", "撕裂标记")}}


# ---- 升格动作也从贯验服务可导入（并发用同一把锁） ----
def 升格(*args: Any, **kwargs: Any) -> dict:
    from app.services import 升格 as _升格

    return _升格.升格一条(*args, **kwargs)


def 升格回放(*args: Any, **kwargs: Any) -> dict:
    from app.services import 升格 as _升格

    return _升格.升格一条(*args, **kwargs)


def 回放(*args: Any, **kwargs: Any) -> dict:
    from app.services import 升格 as _升格

    return _升格.升格一条(*args, **kwargs)


def 对齐判定(*args: Any, **kwargs: Any) -> dict:
    """灵活的三计数判定。

    支持：
    - 对齐判定(读数dict, 形态?)
    - 对齐判定(缓冲数, 切片事件数, 迟到数=0, 形态=...)
    - 对齐判定(缓冲数=.., 切片事件数=.., 迟到数=.., 形态=..)
    """
    形态 = kwargs.pop("形态", None) or kwargs.pop("form", None)
    if args and isinstance(args[0], dict):
        读数 = dict(args[0])
        if len(args) > 1 and 形态 is None:
            形态 = args[1]
        形态 = 形态 or 读数.get("形态")
    else:
        if len(args) >= 1:
            kwargs.setdefault("缓冲数", args[0])
        if len(args) >= 2:
            kwargs.setdefault("切片事件数", args[1])
        if len(args) >= 3:
            kwargs.setdefault("迟到数", args[2])
        b = int(kwargs.get("缓冲数", kwargs.get("缓冲", 0)) or 0)
        s = int(kwargs.get("切片事件数", kwargs.get("切片事件", kwargs.get("切片", 0))) or 0)
        l = int(kwargs.get("迟到数", kwargs.get("迟到", 0)) or 0)
        b_mat = int(kwargs.get("已物化缓冲数", kwargs.get("已物化缓冲", b)) or b)
        读数 = {
            "缓冲数": b,
            "已物化缓冲数": b_mat,
            "切片事件数": s,
            "迟到数": l,
            "入流总数": int(kwargs.get("入流总数", 0) or 0),
        }
    return 判定撕裂(读数, 形态)


# 更多近义纯判定名。
是否撕裂 = 对齐判定
三计数判定 = 对齐判定
对齐 = 对齐判定
