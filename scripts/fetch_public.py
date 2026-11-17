#!/usr/bin/env python3
"""公版素材与选角引擎：检索 CC0/公有领域图片，支持候选拼图浏览，下载并计算清晰度/微反差客观指标。

用法：
  python fetch_public.py search openverse <关键词> [--limit 8] [--sheet raw/_candidates.png]
  python fetch_public.py search commons   <关键词> [--limit 8] [--sheet raw/_candidates.png]
  python fetch_public.py search cma       <关键词> [--type Photograph] [--limit 8] [--sheet raw/_candidates.png]
  python fetch_public.py search aic       <关键词> [--limit 8] [--sheet raw/_candidates.png]
  python fetch_public.py get <图片URL> <输出文件> --title <标题> --license <许可> --page <来源页>

自动读取系统代理或常见本地端口（127.0.0.1:12000 / 7890）。
get 会把出处与客观画质指标（sharpness / contrast）追加到输出文件同目录的 sources.json。
"""
import argparse
import json
import os
import socket
import sys

import cv2
import numpy as np
import requests

UA = {"User-Agent": "collage-cover-maker/2.0 (public-domain editorial casting)"}
OK_LICENSE = ("cc0", "public domain", "pd", "pdm", "no known copyright", "no restrictions")


def get_session():
    s = requests.Session()
    s.headers.update(UA)
    if not (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")):
        for port in (12000, 7890, 10809):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    p = f"http://127.0.0.1:{port}"
                    s.proxies.update({"http": p, "https": p})
                    break
            except OSError:
                pass
    return s


SESSION = get_session()


def usable(lic):
    l = (lic or "").lower()
    return any(k in l for k in OK_LICENSE) and "by" not in l.replace("public domain", "")


def search_cma(q, limit, art_type=None):
    params = {"q": q, "cc0": 1, "has_image": 1, "limit": limit}
    if art_type:
        params["type"] = art_type
    r = SESSION.get("https://openaccess-api.clevelandart.org/api/artworks/", params=params, timeout=30)
    r.raise_for_status()
    out = []
    for d in r.json().get("data", []):
        im = d.get("images") or {}
        big = im.get("print") or im.get("full") or im.get("web") or {}
        web = im.get("web") or big
        out.append({
            "source": "CMA",
            "title": d["title"],
            "type": d.get("type", ""),
            "license": d.get("share_license_status") or "CC0",
            "url": big.get("url"),
            "thumb": web.get("url"),
            "size": f'{big.get("width")}x{big.get("height")}',
            "page": d.get("url"),
        })
    return out


def search_aic(q, limit):
    r = SESSION.get("https://api.artic.edu/api/v1/artworks/search", params={
        "q": q,
        "query[term][is_public_domain]": "true",
        "fields": "id,title,image_id,artwork_type_title,is_public_domain",
        "limit": limit,
    }, timeout=30)
    r.raise_for_status()
    out = []
    for d in r.json().get("data", []):
        iid = d.get("image_id")
        if not iid:
            continue
        out.append({
            "source": "AIC",
            "title": d.get("title", "Untitled"),
            "type": d.get("artwork_type_title", ""),
            "license": "CC0",
            "url": f"https://www.artic.edu/iiif/2/{iid}/full/1600,/0/default.jpg",
            "thumb": f"https://www.artic.edu/iiif/2/{iid}/full/400,/0/default.jpg",
            "size": "1600w+",
            "page": f"https://www.artic.edu/artworks/{d['id']}",
        })
    return out


def search_commons(q, limit):
    r = SESSION.get("https://commons.wikimedia.org/w/api.php", timeout=30, params={
        "action": "query", "generator": "search", "gsrsearch": q + " filetype:bitmap", "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600, "format": "json"})
    r.raise_for_status()
    out = []
    for p in (r.json().get("query", {}).get("pages", {})).values():
        ii = p["imageinfo"][0]
        lic = ii["extmetadata"].get("LicenseShortName", {}).get("value")
        out.append({
            "source": "Commons",
            "title": p["title"],
            "type": "Bitmap",
            "license": lic,
            "url": ii.get("thumburl") or ii["url"],
            "thumb": ii.get("thumburl") or ii["url"],
            "size": f'{ii["width"]}x{ii["height"]}',
            "page": ii["descriptionurl"],
        })
    return out


def build_contact_sheet(rows, sheet_path):
    usable_rows = [r for r in rows if usable(r["license"]) and r.get("thumb")][:8]
    if not usable_rows:
        return
    tiles = []
    for idx, r in enumerate(usable_rows, 1):
        cell = np.full((300, 260, 3), 242, np.uint8)
        try:
            resp = SESSION.get(r["thumb"], timeout=15)
            im = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
            if im is not None:
                h, w = im.shape[:2]
                sc = min(240 / w, 240 / h)
                rs = cv2.resize(im, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA)
                oy, ox = 36 + (250 - rs.shape[0]) // 2, (260 - rs.shape[1]) // 2
                cell[oy:oy + rs.shape[0], ox:ox + rs.shape[1]] = rs
                gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                ct = float(gray.std())
                cv2.putText(cell, f"#{idx} {r['source']} ct={ct:.0f}", (8, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 200), 2)
        except Exception:
            cv2.putText(cell, f"#{idx} ERR", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        tiles.append(cell)
    cols = min(4, len(tiles))
    nrows = -(-len(tiles) // cols)
    grid = np.full((nrows * 300, cols * 260, 3), 242, np.uint8)
    for k, t in enumerate(tiles):
        r0, c0 = (k // cols) * 300, (k % cols) * 260
        grid[r0:r0 + 300, c0:c0 + 260] = t
    os.makedirs(os.path.dirname(os.path.abspath(sheet_path)), exist_ok=True)
    cv2.imencode(".png", grid)[1].tofile(sheet_path)
    print(f"候选选角拼图 -> {sheet_path}（打开目视挑选张力最强的一张）")


def search_openverse(q, limit):
    r = SESSION.get("https://api.openverse.org/v1/images/", params={
        "q": q,
        "license": "cc0,pdm",
        "category": "photograph",
        "page_size": limit,
    }, timeout=30)
    r.raise_for_status()
    out = []
    for d in r.json().get("results", []):
        url = d.get("url")
        if not url:
            continue
        w, h = d.get("width") or "?", d.get("height") or "?"
        lic = (d.get("license") or "cc0").upper()
        out.append({
            "source": "Openverse",
            "title": d.get("title") or "Untitled",
            "type": d.get("category") or "Photograph",
            "license": lic,
            "url": url,
            "thumb": d.get("thumbnail") or url,
            "size": f"{w}x{h}",
            "page": d.get("foreign_landing_url") or url,
        })
    return out


def cmd_search(a):
    if a.site == "cma":
        rows = search_cma(a.query, a.limit, a.type)
    elif a.site == "aic":
        rows = search_aic(a.query, a.limit)
    elif a.site == "openverse":
        rows = search_openverse(a.query, a.limit)
    else:
        rows = search_commons(a.query, a.limit)
    for i, r in enumerate(rows, 1):
        flag = "OK  " if usable(r["license"]) else "跳过"
        t_str = f" [{r['type']}]" if r.get("type") else ""
        print(f'{i}. [{flag}]{t_str} {r["title"][:55]} | {r["license"]} | {r["size"]}\n   {r["url"]}\n   {r["page"]}')
    if not rows:
        print("无结果")
    elif a.sheet:
        build_contact_sheet(rows, a.sheet)


def cmd_get(a):
    if not usable(a.license):
        sys.exit(f"FAIL: 许可 {a.license!r} 不是 CC0/公有领域，不入库")
    r = SESSION.get(a.url, timeout=90)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        sys.exit(f"FAIL: 下载失败 {r.status_code} {r.headers.get('content-type')}")
    im = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    if im is None:
        sys.exit("FAIL: 无法解码下载的图片")
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    contrast = round(float(gray.std()), 1)
    sharpness = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "wb").write(r.content)
    reg = os.path.join(os.path.dirname(os.path.abspath(a.out)), "sources.json")
    data = json.load(open(reg, encoding="utf-8-sig")) if os.path.exists(reg) else []
    data = [d for d in data if d.get("file") != os.path.basename(a.out)]
    data.append({
        "file": os.path.basename(a.out),
        "title": a.title,
        "license": a.license,
        "page": a.page,
        "url": a.url,
        "resolution": f"{im.shape[1]}x{im.shape[0]}",
        "contrast_std": contrast,
        "laplacian_var": sharpness,
    })
    json.dump(data, open(reg, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK: {a.out} ({im.shape[1]}x{im.shape[0]}, 反差={contrast}, 锐度={sharpness}) 已登记 sources.json")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("site", choices=["cma", "aic", "commons", "openverse"])
    s.add_argument("query")
    s.add_argument("--type", default=None, help="CMA 类型过滤，如 Photograph")
    s.add_argument("--limit", type=int, default=8)
    s.add_argument("--sheet", default=None, help="生成候选缩略拼图路径")
    s.set_defaults(fn=cmd_search)
    g = sub.add_parser("get")
    g.add_argument("url")
    g.add_argument("out")
    g.add_argument("--title", required=True)
    g.add_argument("--license", required=True)
    g.add_argument("--page", required=True)
    g.set_defaults(fn=cmd_get)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
