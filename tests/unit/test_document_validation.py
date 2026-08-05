import pytest

from app.services.document_validation import InvalidDocument, validate_document


@pytest.mark.parametrize(
    ("data", "filename", "mime"),
    [
        (b"%PDF-1.7\ncontent", "constancia.pdf", "application/pdf"),
        (b"\xff\xd8\xffimage\xff\xd9", "foto.jpeg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\ncontent-IEND-tail", "captura.png", "image/png"),
    ],
)
def test_accepts_allowlisted_signatures(data: bytes, filename: str, mime: str) -> None:
    assert validate_document(data, filename, 1000).mime_type == mime


@pytest.mark.parametrize(
    ("data", "filename", "limit"),
    [
        (b"", "empty.pdf", 100),
        (b"MZ executable", "attack.pdf", 100),
        (b"%PDF-1.7", "attack.jpg", 100),
        (b"%PDF-1.7" + b"x" * 100, "large.pdf", 10),
        (b"\xff\xd8\xffwithout-end", "bad.jpg", 100),
        (b"\x89PNG\r\n\x1a\nwithout-end", "bad.png", 100),
    ],
)
def test_rejects_empty_spoofed_malformed_or_large_files(
    data: bytes, filename: str, limit: int
) -> None:
    with pytest.raises(InvalidDocument):
        validate_document(data, filename, limit)
