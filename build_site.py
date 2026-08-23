# -*- coding: utf-8 -*-
"""원고(MDX) + 템플릿 → index.html"""
import json, re, os, glob

CREDIT_KEYS = [('client','고객사'), ('agency','수행사'), ('period','기간'), ('pm','PM'),
               ('cd','CD'), ('planning','기획'), ('design','디자인'), ('publishing','퍼블리싱'),
               ('dev','개발'), ('role','역할'), ('url','사이트')]
MAX_DETAILS = 6          # 큰 이미지 1장 + 작은 이미지 최대 6장


def parse_mdx(path):
    raw = open(path, encoding="utf-8").read()
    _, fm_raw, body = raw.split("---", 2)
    meta = {}
    for line in fm_raw.strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body.strip()


def img_size(src):
    local = src.lstrip("/")
    if os.path.exists(local):
        try:
            from PIL import Image
            return Image.open(local).size
        except Exception:
            pass
    return 0, 0


def sort_newest_first(entries):
    return sorted(entries, key=lambda e: e.get("date") or "", reverse=True)


def build_work():
    """「일」 — 레이아웃 A(좌측 이미지) 또는 C(상단 이미지)"""
    entries = []
    for path in glob.glob("일/*.mdx"):
        meta, body = parse_mdx(path)
        paras, images = [], []
        for chunk in [c.strip() for c in body.split("\n\n") if c.strip()]:
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", chunk)
            if m:
                w, h = img_size(m.group(2))
                images.append({"src": m.group(2), "alt": m.group(1), "w": w, "h": h})
            elif chunk.startswith("## "):
                paras.append({"t": "h", "v": chunk[3:].strip()})
            else:
                paras.append({"t": "p", "v": chunk})

        # 첫 문단은 리드로 크게 뽑는다
        lead = ""
        rest = list(paras)
        if rest and rest[0]["t"] == "p":
            lead = rest.pop(0)["v"]

        credits = [{"k": ko, "v": meta.get(key, "")} for key, ko in CREDIT_KEYS]
        entries.append({
            "slug": os.path.splitext(os.path.basename(path))[0],
            "title": meta["title"], "label": meta.get("label", meta["title"]),
            "layout": meta.get("layout", "A"),
            "date": meta.get("date", ""), "year": meta.get("year", ""),
            "lead": lead, "body": rest,
            "hero": images[0] if images else None,
            "details": images[1:1 + MAX_DETAILS],
            "extra": images[1 + MAX_DETAILS:],
            "credits": credits,
        })
    return sort_newest_first(entries)


def build_text(folder, section):
    """「글」·「삶」 — 레이아웃 E(가운데 정렬)"""
    entries = []
    for path in glob.glob(f"{folder}/*.mdx"):
        meta, body = parse_mdx(path)
        chunks = [c.strip() for c in body.split("\n\n") if c.strip()]
        credit = ""
        kept = []
        for c in chunks:
            if c.startswith("–") or c.startswith("- 19"):
                credit = c.lstrip("–- ").strip(); continue
            if c.startswith("!["):
                continue                                  # E 레이아웃은 텍스트만
            kept.append(c)

        # 시(연 번호가 있는 원고)는 행이 낱개 문단으로 흩어져 있다 → 연 단위로 묶는다
        is_poem = any(re.fullmatch(r"I{1,3}V?|IV", c) for c in kept)
        blocks, cur = [], []
        if is_poem:
            for c in kept:
                if re.fullmatch(r"I{1,3}V?|IV", c):
                    if cur: blocks.append("\n".join(cur)); cur = []
                else:
                    cur.append(c)
            if cur: blocks.append("\n".join(cur))
        else:
            blocks = kept
        meta_line = " · ".join(v for v in (meta.get("outlet",""), meta.get("award","")) if v)
        entries.append({
            "slug": os.path.splitext(os.path.basename(path))[0],
            "title": meta["title"], "label": meta.get("label", meta["title"]),
            "layout": "E", "date": meta.get("date", ""), "year": meta.get("year", ""),
            "blocks": blocks, "credit": credit or meta_line,
            "section": section,
        })
    return sort_newest_first(entries)


work = build_work()
writing = build_text("글", "글")
life = build_text("삶", "삶")

DATA = json.dumps({"work": work, "writing": writing, "life": life},
                  ensure_ascii=False, separators=(",", ":"))
html = open("_template.html", encoding="utf-8").read()
open("index.html", "w", encoding="utf-8").write(html.replace("/*__DATA__*/null", DATA))

from collections import Counter
print(f"index.html {os.path.getsize('index.html'):,} bytes")
print(f"  일 {len(work)}편  레이아웃 {dict(Counter(w['layout'] for w in work))}")
print(f"     이미지 없음 {sum(1 for w in work if not w['hero'])}편 / "
      f"7장 초과 {sum(1 for w in work if w['extra'])}편")
print(f"  글 {len(writing)}편 / 삶 {len(life)}편")
