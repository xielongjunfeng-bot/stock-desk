#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给「个股深挖」明文页注入一个「往期深挖」区块与导航按钮。

用法（cwd 必须是仓库根目录）：
    python3 tools/inject-archive-nav.py 明文.html <本期期数> <root|archive> "密码"

做什么：
    1. 扫描 archive/deep-dive-*.html，用密码逐个解密，只读出各期的
       期数、标题、数据截止日（解出来的明文只在内存里，不落盘）。
    2. 把本期也算进去，按期数倒序生成一份「往期深挖」列表。
    3. 就地改写传入的明文文件：导航条加一个「往期」按钮，footer 前插入列表区块。
    4. 幂等：已存在的区块会被替换，可以反复跑。

位置参数说明：
    root    —— 这份明文将被加密成仓库根目录的 deep-dive.html
    archive —— 这份明文将被加密成 archive/deep-dive-N.html
    两者的相对路径不同（archive 页要用 ../ 回首页），所以必须显式指定。

本脚本不含密码、不含盐、不含任何标的代码，公开无妨。
明文一律不得提交进仓库（见 .gitignore）。
"""
import sys, os, re, glob, json, base64, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BEGIN = "<!-- ARCHIVE-NAV:BEGIN -->"
END   = "<!-- ARCHIVE-NAV:END -->"

STYLE = """<style>
.pa-list{display:flex;flex-direction:column}
.pa-i{display:flex;gap:10px;align-items:baseline;padding:10px 0;border-top:1px solid #e4e2dd;
 text-decoration:none;color:#16181d}
.pa-i:first-child{border-top:0;padding-top:0}
.pa-n{flex:0 0 46px;font-size:11px;font-weight:700;color:#fff;background:#12141a;
 border-radius:4px;padding:3px 0;text-align:center;letter-spacing:.3px}
.pa-i.cur .pa-n{background:#1f4fd8}
.pa-t{flex:1;min-width:0;font-size:14px;line-height:1.5;font-weight:600}
.pa-i.cur .pa-t{color:#7c8290}
.pa-d{flex:0 0 auto;font-size:12px;color:#7c8290;font-variant-numeric:tabular-nums}
a.pa-i:active .pa-t{color:#1f4fd8}
</style>"""


def decrypt(path, pw):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"var D = (\{.*?\});", s, re.S)
    if not m:
        return None
    D = json.loads(m.group(1))
    key = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"),
                              base64.b64decode(D["salt"]), D["iter"], dklen=32)
    try:
        return AESGCM(key).decrypt(base64.b64decode(D["iv"]),
                                   base64.b64decode(D["ct"]), None).decode("utf-8")
    except Exception:
        return None


def meta_of(plain):
    """从明文里读出 (期数, 标题, 数据截止日 MM-DD)。读不出就返回 None。"""
    h1 = re.search(r"<h1>(.*?)</h1>", plain, re.S)
    sub = re.search(r'<div class="sub">(.*?)</div>', plain, re.S)
    if not h1 or not sub:
        return None
    t = re.sub(r'<span class="probadge">.*?</span>', "", h1.group(1), flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^个股深挖\s*·\s*", "", t)
    subtxt = re.sub(r"<[^>]+>", " ", sub.group(1))
    mi = re.search(r"第\s*(\d+)\s*期", subtxt)
    md = re.search(r"数据截至\s*(\d{4})-(\d{2})-(\d{2})", subtxt)
    if not mi:
        return None
    return int(mi.group(1)), t, (f"{md.group(2)}-{md.group(3)}" if md else "")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def build_block(items, cur_issue, where):
    rows = []
    for n, title, date in items:
        href = (f"archive/deep-dive-{n}.html" if where == "root"
                else f"deep-dive-{n}.html")
        if n == cur_issue:
            rows.append(
                f'<div class="pa-i cur"><span class="pa-n">第{n}期</span>'
                f'<span class="pa-t">{esc(title)}　（本期）</span>'
                f'<span class="pa-d">{date}</span></div>')
        else:
            rows.append(
                f'<a class="pa-i" href="{href}"><span class="pa-n">第{n}期</span>'
                f'<span class="pa-t">{esc(title)}</span>'
                f'<span class="pa-d">{date}</span></a>')
    lead = (f"全部 {len(items)} 期都在这里，点一下直达。"
            "已经解锁过就不会再要密码——全站共用同一把钥匙。"
            "日期是各期的数据截止日。")
    return "\n".join([
        BEGIN, STYLE,
        '<h2 id="past"><span class="n">往期</span>往期深挖</h2>',
        f'<p class="lead">{lead}</p>',
        '<div class="card"><div class="pa-list">',
        "\n".join(rows),
        "</div></div>", END, ""])


def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    src, cur_issue, where, pw = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    if where not in ("root", "archive"):
        print("位置参数只能是 root 或 archive"); sys.exit(1)

    plain = open(src, encoding="utf-8").read()

    # 1) 收集全部期次
    found = {}
    for f in glob.glob(os.path.join("archive", "deep-dive-*.html")):
        p = decrypt(f, pw)
        if not p:
            print(f"! 跳过（解不开）：{f}"); continue
        m = meta_of(p)
        if m:
            found[m[0]] = m
    m_self = meta_of(plain)
    if m_self:
        found[m_self[0]] = m_self
    else:
        found.setdefault(cur_issue, (cur_issue, f"第 {cur_issue} 期", ""))
    items = [found[k] for k in sorted(found, reverse=True)]

    # 2) 幂等：先清掉旧区块
    plain = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", plain, flags=re.S)
    plain = plain.replace('<a href="#past">往期</a>', "")

    # 3) 导航条加按钮（插在 nav 内最后一个链接之后）
    def nav_fix(mo):
        return mo.group(0).replace("</div></nav>", '<a href="#past">往期</a></div></nav>')
    plain, n1 = re.subn(r"<nav>.*?</div></nav>", nav_fix, plain, count=1, flags=re.S)

    # 4) 相对路径：archive 页的「← 首页」要回上一级
    n2 = 0
    if where == "archive":
        plain, n2 = re.subn(r'href="\./"', 'href="../"', plain)
        plain = plain.replace(
            '<a href="../deep-dive.html">最新一期 →</a>', "")
        plain, _ = re.subn(r"<nav>.*?</div></nav>",
                           lambda mo: mo.group(0).replace(
                               "</div></nav>",
                               '<a href="../deep-dive.html">最新一期 →</a></div></nav>'),
                           plain, count=1, flags=re.S)

    # 5) 插入区块（footer 之前；没有 footer 就放 </div></body> 之前）
    block = build_block(items, cur_issue, where)
    if "<footer" in plain:
        plain = plain.replace("<footer", block + "\n<footer", 1)
    else:
        plain = plain.replace("</body>", block + "\n</body>", 1)

    open(src, "w", encoding="utf-8").write(plain)
    print(f"已注入往期导航：{src}（共 {len(items)} 期，位置 {where}，"
          f"导航按钮 {n1} 处，首页链接修正 {n2} 处）")


if __name__ == "__main__":
    main()
