# Phase 6 traceability

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Private storage | AWS SigV4 R2 client; no public URL | `tests/unit/test_r2.py` |
| Authorized association | Assigned active gestor plus reply/folio | document repository/service tests |
| File allow-list | PDF/JPEG/PNG signature and extension checks | validation parameter tests |
| Maximum size | 10 MB configurable precondition | negative validation tests |
| Integrity | SHA-256 before persistence | ingestion service test |
| Retention | Database expiration plus R2 lifecycle at 30 days | migration and JSON validation |
| Privacy | Opaque keys and metadata-only audit | threat-model review |
