import uuid

import pytest

from app.core.phone import InvalidPhoneNumber, normalize_phone
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_refresh_token,
    new_refresh_token,
)


@pytest.mark.parametrize(
    "raw",
    [
        "0712345678",
        "0712 345 678",
        "254712345678",
        "+254712345678",
        "+254-712-345678",
        "00254712345678",
        "(0712) 345678",
    ],
)
def test_kenyan_numbers_normalise_to_e164(raw):
    assert normalize_phone(raw) == "+254712345678"


def test_foreign_numbers_keep_their_country_code():
    assert normalize_phone("+250 788 123 456") == "+250788123456"


@pytest.mark.parametrize("raw", ["", "12", "abc", "+0123456789", "07123456789012345678"])
def test_invalid_numbers_are_refused(raw):
    with pytest.raises(InvalidPhoneNumber):
        normalize_phone(raw)


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    token, lifetime = create_access_token(user_id, ["REPORTER"])
    claims = decode_access_token(token)
    assert claims.user_id == user_id
    assert claims.roles == ["REPORTER"]
    assert lifetime == 15 * 60


def test_tampered_token_is_rejected():
    token, _ = create_access_token(uuid.uuid4(), ["REPORTER"])
    with pytest.raises(InvalidTokenError):
        decode_access_token(token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))


def test_refresh_tokens_are_random_and_stored_hashed():
    a, a_hash, _ = new_refresh_token()
    b, _, _ = new_refresh_token()
    assert a != b
    assert a_hash == hash_refresh_token(a)
    assert a not in a_hash


def test_storage_keys_cannot_escape_the_upload_folder(tmp_path):
    from app.storage.local import LocalPhotoStorage

    storage = LocalPhotoStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.save("../../etc/passwd", b"x")
    assert storage.read("../../etc/passwd") is None
