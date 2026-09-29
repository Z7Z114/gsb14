"""纪要加密传输。

运行纪要含有未公开的探测结果（本底计数、疑似信号事件），在通过邮件发给
物理组之前必须先加密。这里使用「HMAC-SHA256 派生密钥流 + HMAC 校验标签」的
轻量方案：不引入第三方密码学库，但保证机密性与完整性。
"""
import base64
import hashlib
import hmac
import os
from typing import Tuple

KEY_LEN = 32


class CryptoError(Exception):
    """密文缺失、密钥错误或完整性校验失败。"""


def _derive_keys(key: bytes) -> Tuple[bytes, bytes]:
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise CryptoError('encryption key must be a non-empty bytes value')
    enc_key = hashlib.sha256(bytes(key) + b'|enc').digest()
    mac_key = hashlib.sha256(bytes(key) + b'|mac').digest()
    return enc_key, mac_key


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(enc_key, nonce + counter.to_bytes(8, 'big'), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def encrypt_payload(plaintext: str, key: str) -> str:
    """返回 base64(nonce || ciphertext || tag)。"""
    if not isinstance(plaintext, str):
        raise CryptoError('plaintext must be a string')
    key_bytes = key.encode('utf-8') if isinstance(key, str) else bytes(key)
    enc_key, mac_key = _derive_keys(key_bytes)
    nonce = os.urandom(16)
    data = plaintext.encode('utf-8')
    stream = _keystream(enc_key, nonce, len(data))
    ciphertext = bytes(a ^ b for a, b in zip(data, stream))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(nonce + ciphertext + tag).decode('ascii')


def decrypt_payload(token: str, key: str) -> str:
    """校验完整性和密钥后解密；任何一步失败都抛 CryptoError。"""
    if not isinstance(token, str) or not token.strip():
        raise CryptoError('ciphertext must be a non-empty string')
    key_bytes = key.encode('utf-8') if isinstance(key, str) else bytes(key)
    enc_key, mac_key = _derive_keys(key_bytes)
    try:
        blob = base64.b64decode(token, validate=True)
    except Exception as exc:
        raise CryptoError(f'invalid base64 ciphertext: {exc}') from exc

    if len(blob) < 16 + 32:
        raise CryptoError('ciphertext too short')

    nonce, body, tag = blob[:16], blob[16:-32], blob[-32:]

    expected_tag = hmac.new(mac_key, nonce + body, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        raise CryptoError('integrity check failed: ciphertext tampered or wrong key')

    stream = _keystream(enc_key, nonce, len(body))
    plaintext = bytes(a ^ b for a, b in zip(body, stream))
    try:
        return plaintext.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise CryptoError(f'plaintext is not valid utf-8: {exc}') from exc
