from httpx import AsyncClient

from app.api.web import build_whatsapp_url


async def test_landing_has_semantic_content_and_no_active_cta(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="es"' in response.text
    assert "WhatsApp disponible próximamente" in response.text
    assert "https://wa.me/" not in response.text
    assert "RFC, CURP ni documentos" in response.text


async def test_legal_pages_are_explicitly_preliminary(client: AsyncClient) -> None:
    for path in ("/privacidad", "/terminos"):
        response = await client.get(path)
        assert response.status_code == 200
        assert "Documento preliminar" in response.text


async def test_search_engine_resources(client: AsyncClient) -> None:
    robots = await client.get("/robots.txt")
    sitemap = await client.get("/sitemap.xml")
    assert robots.status_code == 200
    assert "Sitemap: http://localhost:8000/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "<loc>http://localhost:8000/privacidad</loc>" in sitemap.text


def test_whatsapp_url_contains_only_configured_message() -> None:
    url = build_whatsapp_url("525512345678", "Hola, quiero iniciar una solicitud.")
    assert url == ("https://wa.me/525512345678?text=Hola%2C%20quiero%20iniciar%20una%20solicitud.")
    assert build_whatsapp_url(None, "Hola") is None
