# Phase 6 threat model

## Assets and trust boundaries

Document bytes cross Meta, the application and private Cloudflare R2. PostgreSQL stores only
metadata, a SHA-256 digest, an opaque object key and the expiration timestamp. R2 has no public
bucket or public object URL requirement.

## Controls

- Webhook HMAC validation occurs before parsing or media retrieval.
- Only the active gestor assigned to the request can associate a document.
- Association requires a reply to a recorded request message or an exact request folio in caption.
- Meta download URLs are restricted to HTTPS on `lookaside.fbsbx.com`; redirects are disabled.
- PDF, JPEG and PNG are detected from binary signatures and checked against the filename.
- The application rejects empty, malformed, mismatched and over-10 MB files.
- Object keys are random and do not include client identifiers or original filenames.
- Audit metadata excludes captions, object contents, object keys and personal identifiers.
- R2 lifecycle deletion applies to `requests/` objects at 30 days (2,592,000 seconds).

## Residual risks

- Signature checks are not malware scanning. Antivirus/content disarm remains a production
  hardening requirement before documents can be delivered to a client.
- An R2 upload can become orphaned if PostgreSQL fails immediately afterward. The lifecycle rule
  bounds retention to 30 days; reconciliation belongs to Phase 9.
- Lifecycle deletion can occur asynchronously after expiration. Cloudflare documents that removal
  is typically completed within 24 hours of the expiration value.
