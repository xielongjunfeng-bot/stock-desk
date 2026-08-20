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
- `tools/inject-archive-nav.py` — 给深挖明文页注入「往期深挖」列表与导航（不含密钥与标的，公开无妨）
- `archive/deep-dive-N.html` — 深挖第 N 期存档（密文），链接永久稳定

## 深挖页的往期机制

每期发布时，同一份密文同时写入两个位置：

- `deep-dive.html`（根目录，永远是最新一期）
- `archive/deep-dive-N.html`（存档，地址此后不再变化）

两份的唯一差别是相对路径：根目录版用 `./` 回首页、往期链接写 `archive/deep-dive-N.html`；
存档版用 `../` 回首页、往期链接写 `deep-dive-N.html`。这个差别由
`inject-archive-nav.py` 的第三个参数（`root` / `archive`）控制。

发布流程（加密之前）：

```
python3 tools/inject-archive-nav.py <明文> <N> archive "$PW"   # 存档版
python3 tools/encrypt.py <明文> archive/deep-dive-<N>.html "$PW" "个股深挖 · 投资台" "$SALT"
python3 tools/inject-archive-nav.py <明文> <N> root "$PW"      # 根目录版（脚本幂等，可在同一份明文上重跑）
python3 tools/encrypt.py <明文> deep-dive.html "$PW" "个股深挖 · 投资台" "$SALT"
```

`inject-archive-nav.py` 会扫描 `archive/` 下全部密文页、逐个解密后只读出期数、
标题与数据截止日来拼列表，解出的明文只在内存里，不落盘。标的名只出现在加密后的
正文里，仓库明文（README、脚本、state.json）一律不含标的代码。

明文源文件不入库，见 `.gitignore`。
