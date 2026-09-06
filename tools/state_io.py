#!/usr/bin/env python3
"""
state_io.py — 投资台加密状态文件读写工具（v8 状态外置）
用同一套 PBKDF2-SHA256(310000) + AES-256-GCM，与页面加密同盐，
所以同一个密码管全站页面 + 状态文件。

用法：
  读取:  python3 tools/state_io.py get <file.enc> "<密码>"          # JSON 打到 stdout
  写入:  python3 tools/state_io.py put <file.enc> "<密码>"  < in.json # 从 stdin 读 JSON
文件不存在时 get 返回 {} 并退出码 3（调用方可据此初始化）。
写入前会先校验 stdin 是合法 JSON，防止把坏数据写进状态。
"""
import sys, os, json, base64, hashlib, secrets

SALT_B64 = "TOvNJa63CbHBbdNwWH8Clg=="
ITER = 310000

def _key(pw: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), base64.b64decode(SALT_B64), ITER, dklen=32)

def main():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(sys.argv) != 4 or sys.argv[1] not in ("get", "put"):
        print(__doc__, file=sys.stderr); sys.exit(2)
    op, path, pw = sys.argv[1], sys.argv[2], sys.argv[3]
    if op == "get":
        if not os.path.exists(path):
            print("{}"); sys.exit(3)
        blob = json.loads(open(path, encoding="utf-8").read())
        assert blob.get("salt") == SALT_B64, "盐不一致"
        pt = AESGCM(_key(pw)).decrypt(base64.b64decode(blob["iv"]), base64.b64decode(blob["ct"]), None)
        obj = json.loads(pt.decode("utf-8"))          # 校验确为 JSON
        print(json.dumps(obj, ensure_ascii=False, indent=1))
    else:
        obj = json.loads(sys.stdin.read())             # 坏 JSON 在这里直接崩，不落盘
        iv = secrets.token_bytes(12)
        ct = AESGCM(_key(pw)).encrypt(iv, json.dumps(obj, ensure_ascii=False).encode(), None)
        blob = {"salt": SALT_B64, "iter": ITER,
                "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}
        tmp = path + ".tmp"
        open(tmp, "w", encoding="utf-8").write(json.dumps(blob))
        os.replace(tmp, path)                          # 原子替换，写一半不损坏旧状态
        print("OK", path, len(ct), "bytes")

if __name__ == "__main__":
    main()
