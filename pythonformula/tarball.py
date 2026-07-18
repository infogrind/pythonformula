import hashlib
import urllib.request


def sha256_of_url(url: str) -> str:
    digest = hashlib.sha256()
    with urllib.request.urlopen(url) as response:
        while chunk := response.read(65536):
            digest.update(chunk)
    return digest.hexdigest()
