# -*- coding: utf-8 -*-
"""从京东搜索结果抓商品主图，替换 static/products/p1-8.jpg（需浏览器已登录京东）。"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

KEYWORDS = {
    "p1": "智能快递柜",
    "p2": "气泡膜加厚",
    "p3": "合金卡车模型1:64货柜车",
    "p4": "保温箱生鲜配送",
    "p5": "手提电子秤行李秤",
    "p6": "搬家打包袋加厚",
    "p7": "车载GPS定位器",
    "p8": "快递打包纸箱五层",
}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUT = "Backend_template/static/products"


def ab(*args):
    r = subprocess.run(["agent-browser"] + list(args), capture_output=True, text=True, timeout=90)
    return r.stdout.strip()


def js(expr):
    r = ab("eval", expr)
    # eval 输出可能带引号/前缀，取最后一行
    return r.splitlines()[-1] if r else ""


for pid, kw in KEYWORDS.items():
    url = f"https://search.jd.com/Search?keyword={urllib.parse.quote(kw)}&enc=utf-8"
    print(f"== {pid} {kw}: {ab('open', url).splitlines()[-1][:60]}")
    ab("wait", "--load", "load")
    # 滚动两屏触发懒加载
    js("window.scrollTo(0, document.body.scrollHeight/2)")
    time.sleep(2)
    js("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    expr = ("JSON.stringify([...document.querySelectorAll('#J_goodsList .gl-item img')]"
            ".map(i => i.src || i.getAttribute('data-lazy-img') || '')"
            ".filter(u => u && u.includes('360buyimg')).slice(0, 5))")
    raw = js(expr).strip().strip('"')
    urls = json.loads(raw) if raw else []
    urls = [u.replace("\\/", "/") for u in urls]
    print("   imgs:", [u[:80] for u in urls[:3]])
    ok = False
    for u in urls:
        u = u.replace("http://", "https://")
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read(2000000)
            if len(data) > 8000 and data[:3] == b"\xff\xd8\xff":
                open(f"{OUT}/{pid}.jpg", "wb").write(data)
                print(f"   saved {pid}.jpg {len(data)//1024}KB <- {u[:80]}")
                ok = True
                break
        except Exception as e:
            print("   try fail:", str(e)[:60])
    if not ok:
        print(f"   !! {pid} 未抓到，保留原图")
print("done")
