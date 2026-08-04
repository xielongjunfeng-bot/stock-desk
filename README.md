# stock-desk

美股 AI 产业链看板。每个交易日美东收盘后自动更新。

页面均以 **AES-256-GCM** 整页加密（PBKDF2-SHA256 / 310,000 轮），
需密码解锁；解密在浏览器本地完成，密码不经过网络。

- `index.html` — 日更看板（密文）
- `deep-dive.html` — 个股深挖（密文）
- `tools/encrypt.py` — 加密脚本（不含任何密钥，公开无妨）
- `tools/decrypt.py` — 解密脚本（本地校验用，同样不含密钥）
- `tools/index-template.html` — 首页版式骨架（纯 CSS + 占位符，无数据）
- `tools/deep-dive-template.html` — 深挖页版式骨架（纯 CSS + 占位符，无数据）
- `tools/state.json` — 深挖期数游标

明文源文件不入库，见 `.gitignore`。
