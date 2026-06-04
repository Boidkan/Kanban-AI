from backend.auth import hash_password, verify_password


def test_hash_is_verifiable() -> None:
    hashed = hash_password("password")
    assert hashed != "password"
    assert verify_password("password", hashed) is True


def test_same_password_hashes_differently_but_both_verify() -> None:
    first = hash_password("password")
    second = hash_password("password")
    assert first != second  # random salt
    assert verify_password("password", first) is True
    assert verify_password("password", second) is True


def test_wrong_password_does_not_verify() -> None:
    hashed = hash_password("password")
    assert verify_password("wrong", hashed) is False


def test_malformed_or_empty_hash_returns_false() -> None:
    assert verify_password("password", "") is False
    assert verify_password("password", "not-a-valid-argon2-hash") is False
