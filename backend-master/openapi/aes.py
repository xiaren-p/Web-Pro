#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""提供 基于 AES 的基础加密功能"""
# 注意, Windows下使用AES时要安装的是pycryptodome 模块,  Linux/MacOs 下使用AES时要安装的是pycrypto模块
from Crypto.Cipher import AES
import base64
import hashlib

BLOCK_SIZE = 16  # Bytes


def do_pad(text):
    return text + (BLOCK_SIZE - len(text) % BLOCK_SIZE) * \
        chr(BLOCK_SIZE - len(text) % BLOCK_SIZE)


def aes_encrypt(key, data):
    """
    AES的ECB模式加密方法
    :param key: 密钥
    :param data:被加密字符串（明文）
    :return:密文
    """
    # 支持 str 或 bytes 类型的 key
    if isinstance(key, str):
        key_bytes = key.encode('utf-8')
    elif isinstance(key, (bytes, bytearray)):
        key_bytes = bytes(key)
    else:
        raise ValueError('AES key must be str or bytes')

    # AES 密钥长度必须为 16/24/32 字节（ECB 模式）
    if len(key_bytes) not in (16, 24, 32):
        raise ValueError('Invalid AES key length: expected 16, 24 or 32 bytes')

    # 字符串补位
    data = do_pad(data)

    try:
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        # 加密后得到的是bytes类型的数据，使用Base64进行编码,返回字符串
        result = cipher.encrypt(data.encode())
        enc_text = base64.b64encode(result).decode('utf-8')
        return enc_text
    except Exception as e:
        # 捕获任意底层扩展异常，并转换为可控的 Python 异常以避免进程崩溃
        raise ValueError(f'AES encryption failed: {e}') from e


def md5_encrypt(text: str):
    md = hashlib.md5()
    md.update(text.encode('utf-8'))
    return md.hexdigest()
