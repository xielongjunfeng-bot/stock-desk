#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 encrypt.py 生成的加密页解回明文（用于本地校验、读取上一期内容）。

用法：
    python3 decrypt.py 加密页.html "密码" [输出.html]
    不给输出路径则打印到 stdout。

本脚本不含任何密钥，公开无妨。
解出来的明文一律不得提交进仓库（见 .gitignore）。
"""
import sys, re, json, base64, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src, pw = sys.argv[1], sys.argv[2]
    s = open(src, encoding="utf-8").read()
    m = re.search(r"var D = (\{.*?\});", s, re.S)
    if not m:
        print("不是本系统生成的加密页（找不到 payload）"); sys.exit(2)
    D = json.loads(m.group(1))
    key = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"),
                              base64.b64decode(D["salt"]), D["iter"], dklen=32)
    try:
        plain = AESGCM(key).decrypt(base64.b64decode(D["iv"]),
                                    base64.b64decode(D["ct"]), None).decode("utf-8")
    except Exception:
        print("密码不对，或密文已损坏"); sys.exit(3)
    if len(sys.argv) > 3:
        open(sys.argv[3], "w", encoding="utf-8").write(plain)
        print(f"已解密：{src} → {sys.argv[3]}（{len(plain):,} 字节）")
    else:
        sys.stdout.write(plain)

if __name__ == "__main__":
    main()
