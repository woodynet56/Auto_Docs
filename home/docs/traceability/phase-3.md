# Trazabilidad — Fase 3

| Requisito | Componente | Prueba | Resultado |
|---|---|---|---|
| Landing responsive | `templates/index.html`, `static/css/site.css` | `test_landing_has_semantic_content_and_no_active_cta` | Aprobado |
| CTA sin datos personales | `api/web.py` | `test_whatsapp_url_contains_only_configured_message` | Aprobado |
| Privacidad y términos | `templates/privacy.html`, `templates/terms.html` | `test_legal_pages_are_explicitly_preliminary` | Aprobado |
| SEO técnico | `api/web.py`, `templates/base.html` | `test_search_engine_resources` | Aprobado |
| Tema y menú accesible | `static/js/site.js`, `static/css/site.css` | Inspección estática y prueba manual documentada | Aprobado |
| Regresión de salud y dominio | aplicación completa | `pytest` y `smoke_test.py` | Aprobado |

La validación visual en navegadores reales continúa como paso manual previo a producción. Los
textos legales no se consideran aprobados.
