# stock-desk

美股 AI 产业链看板。每个交易日美东收盘后自动更新。

页面均以 **AES-256-GCM** 整页加密（PBKDF2-SHA256 / 310,000 轮），
需密码解锁；解密在浏览器本地完成，密码不经过网络。

- `index.html` — 日更看板（密文）
- `deep-dive.html` — 个股深挖（密文）
- `tools/encrypt.py` — 加密脚本（不含任何密钥，公开无妨）

明文源文件不入库，见 `.gitignore`。
