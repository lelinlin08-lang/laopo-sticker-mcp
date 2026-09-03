from __future__ import annotations

from starlette.testclient import TestClient

from laopo_sticker_mcp.server import create_http_app, create_server


def test_health_and_png_direct_response(settings) -> None:
    app = create_http_app(create_server(settings), settings)
    with TestClient(app, base_url="http://testserver") as client:
        health = client.get("/healthz", follow_redirects=False)
        assert health.status_code == 200
        assert health.json()["ok"] is True

        image = client.get("/media/love_cat_001.png", follow_redirects=False)
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/png")
        assert image.headers["access-control-allow-origin"] == "*"
        assert image.headers["x-content-type-options"] == "nosniff"
        assert image.headers["cache-control"] == "public, max-age=86400"
        assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert image.history == []
