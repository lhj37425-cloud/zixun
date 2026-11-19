"""本机小服务：浏览网页，并允许在网页里按日期手动抓取。

只监听 127.0.0.1，同局域网的其他设备连不上。
用法：uv run dd serve --open（或双击 scripts/serve.bat）
"""

from __future__ import annotations

import json
import threading
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from daily_dissect import paths
from daily_dissect.radar.run import run_radar
from daily_dissect.web.build import build_site

BEIJING = timezone(timedelta(hours=8))

# 同一时间只跑一次抓取，避免连点两次把数据写乱
_RUN_LOCK = threading.Lock()


def available_days() -> list[str]:
    """content/daily/ 里已经有数据的日期，新的在前。"""
    folder = paths.CONTENT_DIR / "daily"
    if not folder.exists():
        return []
    return sorted((path.stem for path in folder.glob("*.json")), reverse=True)


def refresh_day(day: date) -> dict:
    """抓取指定日期，再重新生成网页；返回给页面用的结果。"""
    today = datetime.now(BEIJING).date()
    if day > today:
        raise ValueError("不能抓未来的日期")
    backfill = day < today
    with _RUN_LOCK:
        report = run_radar(today=day, backfill=backfill)
        build_site()
    return {
        "ok": bool(report.projects_ok or report.news_ok),
        "date": day.isoformat(),
        "backfill": backfill,
        "projects": {
            "ok": report.projects_ok,
            "error": report.document["projects"].get("error"),
        },
        "news": {
            "ok": report.news_ok,
            "error": report.document["news"].get("error"),
            "count": len(report.document["news"].get("items") or []),
        },
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(paths.SITE_DIR), **kwargs)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802（http.server 规定的方法名）
        if urlparse(self.path).path == "/api/days":
            days = available_days()
            self._send_json({"days": days, "latest": days[0] if days else ""})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/radar":
            self._send_json({"ok": False, "error": "没有这个接口"}, 404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
            day_text = str(payload.get("date") or "") if isinstance(payload, dict) else ""
            day = date.fromisoformat(day_text)
        except (ValueError, TypeError):
            self._send_json({"ok": False, "error": "日期格式不对，例如 2026-11-13"}, 400)
            return
        try:
            result = refresh_day(day)
        except ValueError as error:
            self._send_json({"ok": False, "error": str(error)}, 400)
            return
        except Exception as error:  # 抓取失败时把原因还给页面，不让服务挂掉
            self._send_json(
                {"ok": False, "error": str(error) or error.__class__.__name__},
                500,
            )
            return
        self._send_json(result)


def serve(port: int = 8765, open_browser: bool = False) -> None:
    build_site()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/index.html"
    print(f"本地服务已启动：{url}")
    print("网页里的「抓取这一天」按钮现在可以用了。在这个窗口按 Ctrl+C 停止。")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
