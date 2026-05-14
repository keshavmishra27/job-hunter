import hashlib


def sha256_of_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_of_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
