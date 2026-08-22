# -*- coding: utf-8 -*-
"""원고(MDX) + 템플릿 → index.html"""
import json, re, os, glob

def sort_newest_first(entries):
    """드로어는 최신이 위, 오래된 것이 아래."""
    return sorted(entries, key=lambda e: e.get("date") or "", reverse=True)


def parse_mdx(path):
    raw = open(path, encoding="utf-8").read()
    _, fm_raw, body = raw.split("---", 2)
    meta = {}
    for line in fm_raw.strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body.strip()


def build_writing():
    """「글」 — 연(stanza) 단위 시"""
    entries = []
    for path in glob.glob("글/*.mdx"):
        meta, body = parse_mdx(path)
        stanzas, cur, credit = [], None, ""
        for line in body.split("\n"):
            s = line.strip()
            if re.fullmatch(r"I{1,3}V?|IV", s):
                cur = {"no": s, "lines": []}
                stanzas.append(cur)
            elif s.startswith("–") and "우수상" in s:
                credit = s
            elif s and cur is not None:
                cur["lines"].append(s)
        entries.append({
            "slug": os.path.splitext(os.path.basename(path))[0],
            "title": meta["title"], "label": meta.get("label", meta["title"]),
            "date": meta.get("date", meta.get("year", "") + "-01-01"),
            "year": meta.get("year", ""),
            "outlet": meta.get("outlet", ""), "award": meta.get("award", ""),
            "stanzas": stanzas, "credit": credit,
        })
    return sort_newest_first(entries)


def build_work():
    """「일」 — 문단·소제목·이미지 블록"""
    entries = []
    for path in glob.glob("일/*.mdx"):
        meta, body = parse_mdx(path)
        blocks = []
        for chunk in [c.strip() for c in body.split("\n\n") if c.strip()]:
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", chunk)
            if m:
                src = m.group(2)
                # 표시 크기를 미리 넣어 이미지 로드 시 레이아웃이 튀지 않게 한다
                w = h = 0
                local = src.lstrip("/")
                if os.path.exists(local):
                    try:
                        from PIL import Image
                        w, h = Image.open(local).size
                    except Exception:
                        pass
                blocks.append({"t": "img", "alt": m.group(1), "src": src,
                               "w": w, "h": h})
            elif chunk.startswith("## "):
                blocks.append({"t": "h", "v": chunk[3:].strip()})
            else:
                blocks.append({"t": "p", "v": chunk})
        # 이미지가 7장 이상인 글은 연속된 이미지를 격자로 묶는다.
        # 세로로 쌓으면 본문보다 이미지가 압도적으로 길어져 스크롤 마라톤이 된다.
        if sum(1 for b in blocks if b["t"] == "img") > 6:
            merged = []
            for b in blocks:
                if b["t"] == "img" and merged and merged[-1]["t"] == "gallery":
                    merged[-1]["items"].append(b)
                elif b["t"] == "img":
                    merged.append({"t": "gallery", "items": [b]})
                else:
                    merged.append(b)
            blocks = merged

        entries.append({
            "slug": os.path.splitext(os.path.basename(path))[0],
            "title": meta["title"], "label": meta.get("label", meta["title"]),
            "date": meta.get("date", meta.get("year", "") + "-01-01"),
            "year": meta.get("year", ""),
            "period": meta.get("period", ""), "org": meta.get("org", ""),
            "role": meta.get("role", ""), "blocks": blocks,
        })
    return sort_newest_first(entries)


writing, work = build_writing(), build_work()
DATA = json.dumps({"writing": writing, "work": work}, ensure_ascii=False, indent=2)

html = open("_template.html", encoding="utf-8").read()
html = html.replace("/*__DATA__*/null", DATA)
open("index.html", "w", encoding="utf-8").write(html)

print(f"index.html {os.path.getsize('index.html'):,} bytes")
print(f"  글 {len(writing)}편")
for w in writing: print(f"     {w['date']}  {w['label']}")
print(f"  일 {len(work)}편")
for w in work: print(f"     {w['date']}  {w['label']}")
for w in work:
    kinds = {}
    for b in w["blocks"]:
        kinds[b["t"]] = kinds.get(b["t"], 0) + 1
    print(f"     └ 블록 {kinds}")
