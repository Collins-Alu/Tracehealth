from app.core.security import hash_password, verify_password


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("S3cure-passphrase")
    assert hashed != "S3cure-passphrase"
    assert hashed.startswith("$argon2id$")
    assert verify_password("S3cure-passphrase", hashed)


def test_wrong_password_is_rejected():
    assert not verify_password("wrong", hash_password("right-one"))


def test_malformed_hash_is_rejected_not_crashing():
    assert not verify_password("anything", "not-a-hash")

