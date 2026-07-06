from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from clashtx import AUTHOR
from clashtx.controller import ClashTXController

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SubscriptionPayload(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)


class ModePayload(BaseModel):
    mode: str


class SortPayload(BaseModel):
    sort_mode: str


class GroupPayload(BaseModel):
    group: str


class NodeSelectPayload(BaseModel):
    group: str
    node: str


class NodeTestPayload(BaseModel):
    node: str


class ProxyApplyPayload(BaseModel):
    host: str
    port: int
    no_proxy: str


class NetworkModePayload(BaseModel):
    mode: str


def create_app(controller: ClashTXController | None = None) -> FastAPI:
    ctl = controller or ClashTXController()
    app = FastAPI(
        title="ClashTX Web UI",
        description=f"ClashTerminalX web interface · {AUTHOR}",
        docs_url="/api/docs",
        redoc_url=None,
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/dashboard")
    def dashboard() -> dict:
        return ctl.dashboard()

    @app.get("/api/traffic")
    def traffic() -> dict:
        return ctl.traffic()

    @app.post("/api/service/{action}")
    def service_action(action: str) -> dict[str, str]:
        try:
            message = ctl.service_action(action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": message}

    @app.get("/api/subscriptions")
    def list_subscriptions() -> list[dict]:
        return ctl.list_subscriptions()

    @app.post("/api/subscriptions")
    def save_subscription(payload: SubscriptionPayload) -> dict:
        try:
            return ctl.save_subscription(payload.name.strip(), payload.url.strip())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/subscriptions/{name}/activate")
    def activate_subscription(name: str) -> dict:
        try:
            return ctl.activate_subscription(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/subscriptions/{name}/refresh")
    def refresh_subscription(name: str) -> dict:
        try:
            return ctl.refresh_subscription(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/subscriptions/refresh-all")
    def refresh_all_subscriptions() -> dict:
        try:
            return ctl.refresh_all_subscriptions()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.delete("/api/subscriptions/{name}")
    def delete_subscription(name: str) -> dict:
        try:
            return ctl.delete_subscription(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/nodes")
    def list_nodes() -> dict:
        try:
            return ctl.list_nodes()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/mode")
    def set_mode(payload: ModePayload) -> dict[str, str]:
        if payload.mode in {"system", "tun"}:
            raise HTTPException(
                status_code=400,
                detail="Use /api/network/mode for system or tun network mode.",
            )
        try:
            ctl.set_mode(payload.mode)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": f"Mode switched to {payload.mode}."}

    @app.post("/api/network/mode")
    def set_network_mode(payload: NetworkModePayload) -> dict[str, str]:
        if payload.mode not in {"system", "tun"}:
            raise HTTPException(status_code=400, detail="Mode must be system or tun")
        try:
            message = ctl.set_network_mode(payload.mode)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": message}

    @app.post("/api/sort")
    def set_sort(payload: SortPayload) -> dict[str, str]:
        ctl.set_sort_mode(payload.sort_mode)
        return {"message": f"Sort mode set to {payload.sort_mode}."}

    @app.post("/api/nodes/group")
    def set_active_group(payload: GroupPayload) -> dict[str, str]:
        ctl.set_active_node_group(payload.group.strip())
        return {"message": f"Active group set to {payload.group}."}

    @app.post("/api/nodes/select")
    def select_node(payload: NodeSelectPayload) -> dict[str, str]:
        try:
            updated = ctl.select_node(payload.group, payload.node)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if len(updated) > 1:
            message = f"Selected {payload.node} for {payload.group} (synced: {', '.join(updated)})"
        else:
            message = f"Selected {payload.node} for {payload.group}."
        return {"message": message, "groups": ",".join(updated)}

    @app.post("/api/nodes/test")
    def test_node(payload: NodeTestPayload) -> dict[str, int | str]:
        try:
            delay = ctl.test_node(payload.node)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"node": payload.node, "delay": delay}

    @app.post("/api/nodes/test-all/start")
    def start_test_all() -> dict[str, str]:
        try:
            ctl.start_test_all_async()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Concurrent latency test started."}

    @app.get("/api/nodes/test-all/status")
    def test_all_status() -> dict:
        return ctl.test_all_progress()

    @app.post("/api/nodes/test-all")
    def test_all_nodes() -> dict:
        try:
            return ctl.test_all_nodes()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/network")
    def network_status() -> dict:
        return ctl.network_status()

    @app.get("/api/proxy")
    def proxy_status() -> dict:
        return ctl.network_status()["proxy"]

    @app.post("/api/proxy/apply")
    def apply_proxy(payload: ProxyApplyPayload) -> dict[str, str]:
        try:
            ctl.apply_proxy(payload.host.strip(), payload.port, payload.no_proxy.strip())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": "Proxy settings saved."}

    @app.post("/api/proxy/enable")
    def enable_proxy() -> dict[str, str]:
        try:
            message = ctl.enable_proxy()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": message}

    @app.post("/api/proxy/disable")
    def disable_proxy() -> dict[str, str]:
        try:
            message = ctl.disable_proxy()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"message": message}

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app


def run_ui(host: str = "0.0.0.0", port: int = 7887) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")
