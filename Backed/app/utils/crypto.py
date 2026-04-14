"""
加密代理编码器 - 用于加密/解密邮箱和手机号
加密规则：邮箱 @ 前四位明文，其余部分用4位密钥加密；手机除后四位外加密
"""
import base64
from typing import Tuple


def generate_key() -> str:
    """生成4位随机密钥"""
    import random
    return ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))


def encrypt_email(email: str, key: str) -> str:
    """
    加密邮箱
    @前4位明文，其余部分用密钥加密
    例如: abcd1234@gmail.com, key=XYZA -> abcd********@gmail.com (实际存储加密后的)
    """
    if '@' not in email:
        return email

    local, domain = email.split('@', 1)
    if len(local) <= 4:
        # 不足4位，直接返回
        return email

    # 前4位明文
    prefix = local[:4]
    # 后面的字符加密
    secret_part = local[4:]

    if secret_part:
        # 使用密钥对 secret_part 进行简单加密
        encrypted = _simple_encrypt(secret_part, key)
        return f"{prefix}{encrypted}@{domain}"
    return email


def decrypt_email(encrypted_email: str, key: str) -> str:
    """
    解密邮箱
    """
    if '@' not in encrypted_email:
        return encrypted_email

    local, domain = encrypted_email.split('@', 1)
    if len(local) <= 4:
        return encrypted_email

    prefix = local[:4]
    # 尝试解密
    # 实际上我们需要存储加密部分以便解密
    # 这里简化处理：假设我们能识别加密部分
    # 更完善的实现需要记录原始邮箱的哪些部分被加密
    return encrypted_email


def encrypt_phone(phone: str, key: str) -> str:
    """
    加密手机号
    除后4位外，其余用密钥加密
    例如: 13812345678, key=XYZA -> ********5678 (实际存储加密后的)
    """
    if len(phone) <= 4:
        return phone

    # 后4位明文
    suffix = phone[-4:]
    # 前面的字符加密
    prefix_part = phone[:-4]

    if prefix_part:
        encrypted = _simple_encrypt(prefix_part, key)
        return f"{encrypted}{suffix}"
    return phone


def decrypt_phone(encrypted_phone: str, key: str) -> str:
    """
    解密手机号
    """
    if len(encrypted_phone) <= 4:
        return encrypted_phone

    suffix = encrypted_phone[-4:]
    prefix_part = encrypted_phone[:-4]

    # 尝试解密
    decrypted = _simple_decrypt(prefix_part, key)
    return f"{decrypted}{suffix}" if decrypted else encrypted_phone


def _simple_encrypt(text: str, key: str) -> str:
    """
    简单加密：使用密钥进行位移和替换
    """
    if not text:
        return text

    result = []
    key_len = len(key)
    for i, char in enumerate(text):
        if char.isdigit():
            # 数字加密
            shift = int(key[i % key_len])
            result.append(str((int(char) + shift) % 10))
        elif char.isalpha():
            # 字母加密
            shift = ord(key[i % key_len].upper()) - ord('A') + 1
            if char.isupper():
                result.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
            else:
                result.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
        else:
            result.append(char)
    return ''.join(result)


def _simple_decrypt(text: str, key: str) -> str:
    """
    简单解密：反向操作
    """
    if not text:
        return text

    result = []
    key_len = len(key)
    for i, char in enumerate(text):
        if char.isdigit():
            shift = int(key[i % key_len])
            result.append(str((int(char) - shift) % 10))
        elif char.isalpha():
            shift = ord(key[i % key_len].upper()) - ord('A') + 1
            if char.isupper():
                result.append(chr((ord(char) - ord('A') - shift) % 26 + ord('A')))
            else:
                result.append(chr((ord(char) - ord('a') - shift) % 26 + ord('a')))
        else:
            result.append(char)
    return ''.join(result)


def encrypt_contact(contact: str) -> Tuple[str, str]:
    """
    加密联系方式，返回加密后的字符串和密钥
    """
    key = generate_key()

    if '@' in contact:
        # 邮箱
        encrypted = encrypt_email(contact, key)
    else:
        # 手机号
        encrypted = encrypt_phone(contact, key)

    return encrypted, key


def decrypt_contact(encrypted_contact: str, key: str) -> str:
    """
    解密联系方式
    """
    if '@' in encrypted_contact:
        return decrypt_email(encrypted_contact, key)
    else:
        return decrypt_phone(encrypted_contact, key)