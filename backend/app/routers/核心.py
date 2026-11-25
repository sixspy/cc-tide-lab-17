from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from pathlib import Path
from app.services import 目录, 装载, 关窗, 贯验, 夹具, 统计, 说明, 升格


async def _body(request: Request) -> dict:
    """容忍空 body / 非 JSON 的请求体解析。"""
    try:
        raw = await request.body()
        if not raw:
            return {}
        return await request.json()
    except Exception:
        return {}


async def api_概览(request: Request):
    return JSONResponse(目录.概览())


async def api_仓情(request: Request):
    return JSONResponse(说明.仓情())


async def api_窗规_get(request: Request):
    return JSONResponse(目录.窗规())


async def api_窗规_post(request: Request):
    body = await request.json()
    return JSONResponse(目录.改窗规(body))


async def api_网点(request: Request):
    return JSONResponse(目录.网点列表())


async def api_观测(request: Request):
    return JSONResponse(目录.观测列表())


async def api_缓冲(request: Request):
    return JSONResponse(目录.缓冲列表())


async def api_切片(request: Request):
    return JSONResponse(目录.切片列表())


async def api_迟到(request: Request):
    qp = request.query_params
    # 默认返回全部迟到行（含 状态=已升格）；?在匣=1 或 ?全部=0 只看在匣。
    if qp.get("在匣") in ("1", "true", "True") or qp.get("仅在匣") in ("1", "true", "True"):
        return JSONResponse(目录.在匣迟到列表())
    全部原始 = qp.get("全部")
    if 全部原始 is not None and 全部原始 in ("0", "false", "False", "否"):
        return JSONResponse(目录.在匣迟到列表())
    return JSONResponse(目录.迟到列表())


async def api_贯验列表(request: Request):
    return JSONResponse(目录.贯验列表())


async def api_夹具(request: Request):
    return JSONResponse(夹具.列表())


async def api_装载(request: Request):
    body = await request.json()
    return JSONResponse(装载.装一批(body))


async def api_夹具装载(request: Request):
    名 = request.path_params["name"]
    try:
        return JSONResponse(装载.装一批(夹具.读取(名)))
    except FileNotFoundError:
        return JSONResponse({"错误": 名}, status_code=404)


async def api_关窗(request: Request):
    return JSONResponse(关窗.关当前窗())


async def api_关窗并贯验(request: Request):
    return JSONResponse(贯验.关窗并贯验())


async def api_贯验(request: Request):
    body = await _body(request)
    form = body.get("形态") or body.get("贯验形态") or request.query_params.get("形态")
    return JSONResponse(贯验.跑一次(form))


async def api_贯验只读(request: Request):
    form = request.query_params.get("形态") or request.query_params.get("贯验形态")
    return JSONResponse(贯验.只读(form))


async def api_贯验形态_get(request: Request):
    form = 贯验.当前形态()
    out = {"形态": form, "工程形态": form, "贯验形态": form}
    # 徽章与三表同票：形态查询同时给当前只读判定与徽章。
    try:
        snap = 贯验.只读(form)
        for k in ("缓冲数", "切片事件数", "迟到数", "撕裂标记", "valid",
                  "是否对齐", "说明", "徽章文", "徽章类", "徽章", "三计数集合"):
            out[k] = snap.get(k)
    except Exception:
        pass
    return JSONResponse(out)


async def api_贯验形态_post(request: Request):
    body = await _body(request)
    return JSONResponse(贯验.选定形态(body))


async def api_旁路凭证(request: Request):
    return JSONResponse(目录.旁路凭证列表())


async def api_升格(request: Request):
    body = await _body(request)
    # Starlette 0.41 路径参数名只接受 ASCII，路由模板用 {id}，
    # 同时兼容可能的 {编号} 命名（其他 ASGI 实现/手工挂载）。
    编号 = request.path_params.get("id") or request.path_params.get("编号")
    目标 = body.get("目标") if isinstance(body, dict) else None
    匣编号 = body.get("匣编号") or body.get("编号") or 编号
    事件编号 = body.get("事件编号") if isinstance(body, dict) else None
    目标窗号 = body.get("目标窗号") or body.get("窗号") if isinstance(body, dict) else None
    if 编号 is not None and str(编号).isdigit():
        匣编号 = int(编号)
    elif 编号 is not None and 匣编号 is None:
        事件编号 = 编号
    res = 升格.升格一条(
        目标, 匣编号=匣编号, 事件编号=事件编号, 目标窗号=目标窗号
    )
    return JSONResponse(res)


async def api_升格全部(request: Request):
    body = await _body(request)
    return JSONResponse(升格.升格全部(body.get("目标窗号") if isinstance(body, dict) else None))


async def api_统计观测(request: Request):
    return JSONResponse(统计.观测命运())


async def api_统计缓冲(request: Request):
    return JSONResponse(统计.缓冲命运())


async def api_空桩(request: Request):
    root = Path(__file__).resolve().parents[1] / "modules"
    out = []
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if p.is_dir() and p.name != "__pycache__" and (p / "__init__.py").is_file():
                out.append(p.name)
    return JSONResponse({"空桩": out, "条数": len(out)})


路由表 = [
    Route("/api/概览", api_概览),
    Route("/api/仓情", api_仓情),
    Route("/api/窗规", api_窗规_get, methods=["GET"]),
    Route("/api/窗规", api_窗规_post, methods=["POST"]),
    Route("/api/网点源", api_网点),
    Route("/api/观测点", api_观测),
    Route("/api/入窗缓冲", api_缓冲),
    Route("/api/窗切片账", api_切片),
    Route("/api/迟到匣", api_迟到),
    Route("/api/窗贯验", api_贯验列表),
    Route("/api/夹具", api_夹具),
    Route("/api/观测点/装载", api_装载, methods=["POST"]),
    Route("/api/观测点/夹具/{name}", api_夹具装载, methods=["POST"]),
    Route("/api/关窗/跑", api_关窗, methods=["POST"]),
    Route("/api/关窗并贯验", api_关窗并贯验, methods=["POST"]),
    Route("/api/关窗/贯验", api_关窗并贯验, methods=["POST"]),
    Route("/api/窗贯验/跑", api_贯验, methods=["POST"]),
    # 三联窗贯验：只读接口（缓冲数/切片事件数/迟到数/撕裂标记/valid）
    Route("/api/窗贯验/只读", api_贯验只读, methods=["GET"]),
    Route("/api/窗贯验只读", api_贯验只读, methods=["GET"]),
    Route("/api/贯验/只读", api_贯验只读, methods=["GET"]),
    Route("/api/贯验只读", api_贯验只读, methods=["GET"]),
    Route("/api/窗贯验/快照", api_贯验只读, methods=["GET"]),
    Route("/api/窗贯验/状态", api_贯验只读, methods=["GET"]),
    # 以题面模块名「三联窗贯验」为前缀的同义接口
    Route("/api/三联窗贯验", api_贯验只读, methods=["GET"]),
    Route("/api/三联窗贯验/只读", api_贯验只读, methods=["GET"]),
    Route("/api/三联窗贯验/状态", api_贯验只读, methods=["GET"]),
    Route("/api/三联窗贯验/跑", api_贯验, methods=["POST"]),
    Route("/api/三联窗贯验/形态", api_贯验形态_post, methods=["POST"]),
    Route("/api/三联窗贯验/形态", api_贯验形态_get, methods=["GET"]),
    # 工程形态选择（三表联查 / 双表加旁路附件）
    Route("/api/窗贯验/形态", api_贯验形态_get, methods=["GET"]),
    Route("/api/窗贯验/形态", api_贯验形态_post, methods=["POST"]),
    Route("/api/窗贯验/策略", api_贯验形态_post, methods=["POST"]),
    # 只读归档旁路凭证（多个兼容路径名）
    Route("/api/旁路凭证", api_旁路凭证, methods=["GET"]),
    Route("/api/归档", api_旁路凭证, methods=["GET"]),
    Route("/api/旁路归档", api_旁路凭证, methods=["GET"]),
    Route("/api/归档旁路凭证", api_旁路凭证, methods=["GET"]),
    # 迟到升格回放（并发互斥 / 原子认领）
    Route("/api/升格", api_升格, methods=["POST"]),
    Route("/api/升格/回放", api_升格, methods=["POST"]),
    Route("/api/升格/全部", api_升格全部, methods=["POST"]),
    Route("/api/升格/回放/全部", api_升格全部, methods=["POST"]),
    Route("/api/升格/{id}", api_升格, methods=["POST"]),
    Route("/api/升格/回放/{id}", api_升格, methods=["POST"]),
    Route("/api/迟到匣/升格", api_升格, methods=["POST"]),
    Route("/api/迟到匣/升格", api_升格, methods=["POST"]),
    Route("/api/迟到匣/升格/{id}", api_升格, methods=["POST"]),
    Route("/api/迟到匣/{id}/升格", api_升格, methods=["POST"]),
    # 中文参数名模板在 Starlette 0.41 不被编译为参数，仅作可读别名保留会失配，
    # 因此额外挂一层纯 ASCII 路径（上面两条）覆盖 /api/迟到匣/1/升格 形态。
    Route("/api/统计/观测命运", api_统计观测),
    Route("/api/统计/缓冲命运", api_统计缓冲),
    Route("/api/空桩", api_空桩),
]
