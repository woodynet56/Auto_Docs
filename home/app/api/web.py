"""Public website routes with no collection of personal data."""

from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.core.config import get_settings

router = APIRouter(include_in_schema=False)
TEMPLATES = Path("app/templates")


def build_whatsapp_url(number: str | None, message: str) -> str | None:
    """Build a WhatsApp link containing only configured, non-personal copy."""
    if number is None:
        return None
    return f"https://wa.me/{number}?text={quote(message, safe='')}"


def render_page(request: Request, content_file: str, title: str) -> HTMLResponse:
    settings = get_settings()
    whatsapp_url = build_whatsapp_url(
        settings.PUBLIC_WHATSAPP_NUMBER, settings.WHATSAPP_INITIAL_MESSAGE
    )
    content = (TEMPLATES / content_file).read_text(encoding="utf-8")
    if whatsapp_url:
        cta = (
            f'<a class="button primary" href="{escape(whatsapp_url, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">'
            'Iniciar solicitud por WhatsApp <span aria-hidden="true">↗</span></a>'
        )
        final_cta = cta
    else:
        cta = (
            '<span class="button disabled" aria-disabled="true">'
            "WhatsApp disponible próximamente</span>"
        )
        final_cta = ""
    content = content.replace("__WHATSAPP_CTA__", cta).replace("__WHATSAPP_FINAL_CTA__", final_cta)
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    page = (
        base.replace("__TITLE__", escape(title))
        .replace("__CANONICAL__", escape(f"{base_url}{request.url.path}", quote=True))
        .replace("__CONTENT__", content)
    )
    return HTMLResponse(page)


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    return render_page(request, "index.html", "Gestoría Reaver | Gestión documental digital")


@router.get("/privacidad", response_class=HTMLResponse)
async def privacy(request: Request) -> HTMLResponse:
    return render_page(request, "privacy.html", "Aviso de privacidad | Gestoría Reaver")


@router.get("/terminos", response_class=HTMLResponse)
async def terms(request: Request) -> HTMLResponse:
    return render_page(request, "terms.html", "Términos de servicio | Gestoría Reaver")


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    base = get_settings().PUBLIC_BASE_URL.rstrip("/")
    return f"User-agent: *\nAllow: /\nDisallow: /docs\nSitemap: {base}/sitemap.xml\n"


@router.get("/sitemap.xml")
async def sitemap() -> Response:
    base = get_settings().PUBLIC_BASE_URL.rstrip("/")
    urls = "".join(
        f"<url><loc>{base}{path}</loc></url>" for path in ("/", "/privacidad", "/terminos")
    )
    body = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(body, media_type="application/xml")
