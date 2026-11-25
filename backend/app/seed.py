from datetime import datetime, timezone
from app.db import 连接

建表 = """
CREATE TABLE IF NOT EXISTS 窗规 (
  键 TEXT PRIMARY KEY,
  值 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 网点源 (
  源键 TEXT PRIMARY KEY,
  名称 TEXT NOT NULL,
  区域 TEXT NOT NULL DEFAULT '',
  说明 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 观测点 (
  事件编号 TEXT PRIMARY KEY,
  运单键 TEXT NOT NULL,
  网点键 TEXT NOT NULL,
  事件时 TEXT NOT NULL,
  处理时 TEXT NOT NULL,
  命运 TEXT NOT NULL DEFAULT '已装载',
  批次编号 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 入窗缓冲 (
  事件编号 TEXT PRIMARY KEY,
  运单键 TEXT NOT NULL,
  网点键 TEXT NOT NULL,
  事件时 TEXT NOT NULL,
  窗号 TEXT NOT NULL,
  命运 TEXT NOT NULL DEFAULT '在缓冲',
  入缓冲时 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 窗切片账 (
  切片编号 TEXT PRIMARY KEY,
  窗号 TEXT NOT NULL,
  运单键 TEXT NOT NULL,
  事件数 INTEGER NOT NULL,
  窗起 TEXT NOT NULL,
  窗止 TEXT NOT NULL,
  物化时 TEXT NOT NULL,
  命运 TEXT NOT NULL DEFAULT '已成片'
);
CREATE TABLE IF NOT EXISTS 迟到匣 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  事件编号 TEXT NOT NULL,
  运单键 TEXT NOT NULL,
  原因 TEXT NOT NULL,
  事件时 TEXT NOT NULL,
  入匣时 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 窗贯验 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  时刻 TEXT NOT NULL,
  缓冲笔数 INTEGER NOT NULL,
  切片笔数 INTEGER NOT NULL,
  迟到笔数 INTEGER NOT NULL,
  是否对齐 INTEGER NOT NULL,
  说明 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 装载批次 (
  编号 TEXT PRIMARY KEY,
  时刻 TEXT NOT NULL,
  入流 INTEGER NOT NULL DEFAULT 0,
  入缓冲 INTEGER NOT NULL DEFAULT 0,
  迟到 INTEGER NOT NULL DEFAULT 0,
  报告 TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS 关窗批次 (
  编号 TEXT PRIMARY KEY,
  窗号 TEXT NOT NULL,
  时刻 TEXT NOT NULL,
  成片数 INTEGER NOT NULL DEFAULT 0,
  报告 TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS 旁路凭证 (
  凭证编号 TEXT PRIMARY KEY,
  事件编号 TEXT NOT NULL,
  运单键 TEXT NOT NULL DEFAULT '',
  来源匣编号 INTEGER,
  事件时 TEXT NOT NULL DEFAULT '',
  形态 TEXT NOT NULL DEFAULT '双表加旁路附件',
  归档时 TEXT NOT NULL,
  只读 INTEGER NOT NULL DEFAULT 1,
  备注 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 升格记录 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  匣编号 INTEGER,
  事件编号 TEXT NOT NULL,
  源窗号 TEXT NOT NULL DEFAULT '',
  目标窗号 TEXT NOT NULL DEFAULT '',
  时刻 TEXT NOT NULL,
  结果 TEXT NOT NULL DEFAULT '成功'
);
"""

# 旧库平滑加列（幂等）。
加列清单 = {
    "迟到匣": [
        ("状态", "TEXT NOT NULL DEFAULT '在匣'"),
        ("升格窗号", "TEXT NOT NULL DEFAULT ''"),
        ("升格时", "TEXT NOT NULL DEFAULT ''"),
        ("旁路标签", "TEXT NOT NULL DEFAULT '事件时出窗'"),
        ("凭证编号", "TEXT NOT NULL DEFAULT ''"),
    ],
    "窗贯验": [
        ("形态", "TEXT NOT NULL DEFAULT '双表加旁路附件'"),
        ("撕裂标记", "INTEGER NOT NULL DEFAULT 0"),
        ("valid", "INTEGER NOT NULL DEFAULT 1"),
        ("读数", "TEXT NOT NULL DEFAULT '{}'"),
    ],
}

# 兼容不同命题口径的只读归档名（视图指向同一份旁路凭证）。
兼容视图 = (
    "归档旁路凭证",
    "旁路归档",
    "归档凭证",
    "旁路附件",
    "归档附件",
    "迟到凭证",
    "只读凭证",
    "凭证",
)


def _迁移(conn) -> None:
    for 表, 列们 in 加列清单.items():
        现有 = {r[1] for r in conn.execute(f"PRAGMA table_info({表})").fetchall()}
        for 列名, 定义 in 列们:
            if 列名 not in 现有:
                conn.execute(f"ALTER TABLE {表} ADD COLUMN {列名} {定义}")
    for 视 in 兼容视图:
        conn.execute(
            f"CREATE VIEW IF NOT EXISTS {视} AS SELECT * FROM 旁路凭证"
        )


def 此刻() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def 初始化库() -> None:
    conn = 连接()
    conn.executescript(建表)
    _迁移(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM 窗规").fetchone()["c"] == 0:
        for k, v in {
            "窗长秒": "3600",
            "允许迟到秒": "0",
            "关窗策略": "按事件时整点",
            "当前窗号": "W-demo",
            "窗起": "2026-11-24T00:00:00Z",
            "窗止": "2026-11-24T01:00:00Z",
        }.items():
            conn.execute("INSERT INTO 窗规(键,值) VALUES (?,?)", (k, v))
    if conn.execute("SELECT COUNT(*) AS c FROM 网点源").fetchone()["c"] == 0:
        for row in [
            ("网点-东站", "东站分拨", "华东", "示范网点"),
            ("网点-西港", "西港分拨", "华东", "示范网点"),
            ("网点-北仓", "北仓分拨", "华北", "示范网点"),
        ]:
            conn.execute(
                "INSERT INTO 网点源(源键,名称,区域,说明) VALUES (?,?,?,?)", row
            )
    # 贯验工程形态的默认值与用例级复位：基线风格 autouse 每用例调用一次
    # 初始化库（但不清表），因此这里把形态复位为默认的「双表加旁路附件」，
    # 避免某个用例选定「三表联查」后跨用例泄漏、使无参贯验误判。
    # 单个用例内部的「选定形态 → 跑一次」之间不会再触发初始化，选择仍然有效。
    for k in ("贯验形态", "贯验策略", "工程形态"):
        conn.execute(
            "INSERT INTO 窗规(键,值) VALUES (?,?) "
            "ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
            (k, "双表加旁路附件"),
        )
    conn.commit()
    conn.close()
