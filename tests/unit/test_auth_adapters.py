from src.adapters.auth.crypto import Argon2AuthAdapter


def test_hash_verify_success():
    auth = Argon2AuthAdapter()
    pwd = "my-secret-password"
    hashed = auth.hash_password(pwd)
    
    assert hashed != pwd
    assert auth.verify_password(pwd, hashed) is True

def test_verify_fail():
    auth = Argon2AuthAdapter()
    pwd = "password"
    hashed = auth.hash_password(pwd)
    
    assert auth.verify_password("wrong", hashed) is False

def test_token_generation():
    auth = Argon2AuthAdapter()
    token1 = auth.create_token("uid", 60)
    token2 = auth.create_token("uid", 60)
    assert len(token1) > 10
    assert token1 != token2
