#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把一个 HTML 文件整页加密成「输密码才能看」的静态页。

用法：
    python3 encrypt.py 明文.html 输出.html "密码" "页面标题" [共享盐base64]

原理：
    PBKDF2-SHA256（310000 轮）从密码派生 256 位密钥 → AES-256-GCM 加密整页 →
    密文以 base64 存进外壳页。浏览器用 WebCrypto 同样的参数解密。
    源代码里只有密文，没有密码、也没有明文，view-source 看到的是乱码。

注意：
    · 本脚本本身不含任何密钥，公开无妨。
    · 明文绝不可提交进公开仓库。
"""
import sys, os, json, base64, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 310_000

SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet">
<meta name="referrer" content="no-referrer">
<title>__TITLE__</title>
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;height:100%}
body{background:#f7f6f3;color:#16181d;display:flex;align-items:center;justify-content:center;
 font:16px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
 padding:20px}
.box{width:100%;max-width:340px;text-align:center}
.lock{font-size:34px;margin-bottom:14px;line-height:1}
h1{font-size:17px;margin:0 0 6px;font-weight:700;letter-spacing:.3px}
.sub{font-size:13px;color:#7c8290;margin:0 0 20px;line-height:1.55}
input{width:100%;padding:13px 14px;font-size:16px;border:1px solid #dcd9d3;border-radius:10px;
 background:#fff;color:#16181d;outline:none;-webkit-appearance:none;text-align:center;letter-spacing:1px}
input:focus{border-color:#12141a}
button{width:100%;margin-top:10px;padding:13px;font-size:15px;font-weight:700;border:0;border-radius:10px;
 background:#12141a;color:#fff;cursor:pointer;font-family:inherit}
button:disabled{opacity:.5;cursor:default}
.msg{font-size:13px;margin-top:12px;min-height:19px;color:#d0342c;line-height:1.5}
.msg.ok{color:#7c8290}
label.rm{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:13px;
 font-size:13px;color:#7c8290;cursor:pointer;user-select:none}
label.rm input{width:auto;padding:0;margin:0}
.foot{margin-top:22px;font-size:11.5px;color:#a8adb8;line-height:1.6}
@media (prefers-color-scheme:dark){html{filter:invert(.93) hue-rotate(180deg)}}
</style>
</head>
<body>
<div class="box" id="gate">
  <div class="lock">🔒</div>
  <h1>__TITLE__</h1>
  <p class="sub">此页面已加密，请输入密码</p>
  <form id="f" autocomplete="on">
    <input id="pw" type="password" inputmode="text" autocomplete="current-password"
           placeholder="密码" aria-label="密码" autofocus>
    <button id="go" type="submit">解锁</button>
  </form>
  <label class="rm"><input type="checkbox" id="rm" checked> 本次浏览器会话内记住</label>
  <div class="msg" id="m"></div>
  <div class="foot">内容以 AES-256-GCM 加密存储<br>解密在你的设备本地完成，密码不会上传</div>
</div>

<script>
var D = __PAYLOAD__;
var KEY = "idk:" + location.origin + location.pathname.replace(/[^/]*$/, "");

function render(html){
  var go=function(){ document.open(); document.write(html); document.close(); };
  if(document.readyState==="complete"){ go(); }
  else{ window.addEventListener("load", function(){ setTimeout(go,0); }); }
}
function b2a(b){var u=new Uint8Array(b),s="";for(var i=0;i<u.length;i++)s+=String.fromCharCode(u[i]);return btoa(s);}
function a2b(a){var s=atob(a),u=new Uint8Array(s.length);for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u;}

async function derive(pw, salt){
  var base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    {name:"PBKDF2", salt:salt, iterations:D.iter, hash:"SHA-256"},
    base, {name:"AES-GCM", length:256}, true, ["decrypt"]);
}

async function open_(pw, silent){
  var m = document.getElementById("m"), go = document.getElementById("go");
  if(!silent){ m.className="msg ok"; m.textContent="解密中…"; go.disabled=true; }
  try{
    var key = await derive(pw, a2b(D.salt));
    var plain = await crypto.subtle.decrypt({name:"AES-GCM", iv:a2b(D.iv)}, key, a2b(D.ct));
    var html = new TextDecoder().decode(plain);
    if(document.getElementById("rm") && document.getElementById("rm").checked){
      try{ sessionStorage.setItem(KEY, b2a(await crypto.subtle.exportKey("raw", key))); }catch(e){}
    }
    render(html);
    return true;
  }catch(e){
    if(!silent){ m.className="msg"; m.textContent="密码不对，再试一次"; go.disabled=false;
      var p=document.getElementById("pw"); p.value=""; p.focus(); }
    try{ sessionStorage.removeItem(KEY); }catch(e2){}
    return false;
  }
}

(async function(){
  // 会话内已解锁过就直接放行
  try{
    var raw = sessionStorage.getItem(KEY);
    if(raw){
      var key = await crypto.subtle.importKey("raw", a2b(raw), {name:"AES-GCM"}, false, ["decrypt"]);
      var plain = await crypto.subtle.decrypt({name:"AES-GCM", iv:a2b(D.iv)}, key, a2b(D.ct));
      var html = new TextDecoder().decode(plain);
      render(html);
      return;
    }
  }catch(e){ try{ sessionStorage.removeItem(KEY); }catch(e2){} }

  document.getElementById("f").addEventListener("submit", function(ev){
    ev.preventDefault();
    var v = document.getElementById("pw").value;
    if(v) open_(v, false);
  });
})();
</script>
</body>
</html>
"""


def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    src, dst, pw, title = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    # 第 5 个参数：base64 盐。同一站点各页传入同一个盐，
    # 解锁一次即可在会话内通行全站（IV 仍逐文件随机，GCM 安全性不受影响）。
    salt = base64.b64decode(sys.argv[5]) if len(sys.argv) > 5 else os.urandom(16)
    plain = open(src, "rb").read()
    iv = os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, ITER, dklen=32)
    ct = AESGCM(key).encrypt(iv, plain, None)

    payload = json.dumps({
        "salt": base64.b64encode(salt).decode(),
        "iv":   base64.b64encode(iv).decode(),
        "ct":   base64.b64encode(ct).decode(),
        "iter": ITER,
    })

    out = SHELL.replace("__PAYLOAD__", payload).replace("__TITLE__", title)
    open(dst, "w", encoding="utf-8").write(out)

    print(f"已加密：{src} → {dst}")
    print(f"  明文 {len(plain):,} 字节 → 密文页 {len(out):,} 字节")
    print(f"  salt(b64) = {base64.b64encode(salt).decode()}")


if __name__ == "__main__":
    main()
