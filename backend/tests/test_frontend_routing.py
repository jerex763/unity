"""Routing contract for the same-origin React production build."""

from django.test import Client, override_settings


def test_frontend_index_serves_root_and_client_routes(tmp_path) -> None:
    marker = b"<html><body>unity-spa-marker</body></html>"
    (tmp_path / "index.html").write_bytes(marker)

    with override_settings(FRONTEND_DIST_DIR=tmp_path):
        root_response = Client().get("/")
        client_route_response = Client().get("/people/123")

    assert root_response.status_code == 200
    assert b"".join(root_response.streaming_content) == marker
    assert client_route_response.status_code == 200
    assert b"".join(client_route_response.streaming_content) == marker


def test_frontend_fallback_does_not_mask_backend_or_asset_routes(tmp_path) -> None:
    marker = b"<html><body>unity-spa-marker</body></html>"
    (tmp_path / "index.html").write_bytes(marker)
    client = Client()

    with override_settings(FRONTEND_DIST_DIR=tmp_path):
        responses = [
            client.get("/api/not-a-real-endpoint/"),
            client.get("/admin/not-a-real-endpoint/"),
            client.get("/static/not-a-real-file.css"),
            client.get("/assets/not-a-real-file.js"),
        ]

    for response in responses:
        assert response.status_code != 200
        assert marker not in response.content
