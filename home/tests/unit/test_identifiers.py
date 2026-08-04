import pytest

from app.db.models.enums import IdentifierType
from app.services.identifiers import (
    IdentifierProtector,
    InvalidIdentifierError,
    identify_and_validate,
    mask_identifier,
    normalize_identifier,
    valid_fernet_key,
)


def test_rfc_and_curp_validation_and_normalization() -> None:
    assert normalize_identifier(" cosc 800113 7na ") == "COSC8001137NA"
    assert identify_and_validate("COSC8001137NA") == (
        IdentifierType.RFC,
        "COSC8001137NA",
    )
    assert identify_and_validate("GODE561231HDFMNN09")[0] == IdentifierType.CURP


@pytest.mark.parametrize("value", ["", "INVALID", "COSC800113", "GODE991399HDFMNN09"])
def test_invalid_identifiers_are_rejected_without_echo(value: str) -> None:
    with pytest.raises(InvalidIdentifierError, match="invalid") as captured:
        identify_and_validate(value)
    if value:
        assert value not in str(captured.value)


def test_mask_encrypt_hash_and_decrypt() -> None:
    key = IdentifierProtector.generate_encryption_key()
    protector = IdentifierProtector(key, "synthetic-hash-key")
    value = "COSC8001137NA"
    encrypted = protector.encrypt(value)
    assert value.encode() not in encrypted
    assert protector.decrypt(encrypted) == value
    assert protector.digest(value) == protector.digest(value)
    assert len(protector.digest(value)) == 64
    assert mask_identifier(value) == "COS*******7NA"
    assert valid_fernet_key(key)
    assert not valid_fernet_key("bad")


def test_protector_rejects_missing_or_invalid_keys() -> None:
    with pytest.raises(RuntimeError, match="not configured"):
        IdentifierProtector("", "")
    with pytest.raises(RuntimeError, match="invalid"):
        IdentifierProtector("bad", "hash")
    with pytest.raises(InvalidIdentifierError, match="Encrypted"):
        IdentifierProtector(IdentifierProtector.generate_encryption_key(), "hash").decrypt(b"bad")
    with pytest.raises(InvalidIdentifierError, match="masked"):
        mask_identifier("SHORT")
