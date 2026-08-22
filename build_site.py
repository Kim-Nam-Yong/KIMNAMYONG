# -*- coding: utf-8 -*-
import json, re, os

SRC = "글/겨울새.mdx"
raw = open(SRC, encoding="utf-8").read()
_, fm, body = raw.split("---", 2)
meta = {}
for line in fm.strip().split("\n"):
    k, v = line.split(":", 1)
    meta[k.strip()] = v.strip()
body = body.strip()

# 시 본문을 연 단위로 쪼갠다: 로마자 섹션 마커 기준
stanzas, cur, credit = [], None, ""
for line in body.split("\n"):
    s = line.strip()
    if re.fullmatch(r"I{1,3}V?|IV", s):
        cur = {"no": s, "lines": []}
        stanzas.append(cur)
    elif s.startswith("–") or s.startswith("-") and "우수상" in s:
        credit = s
    elif s == "":
        continue
    elif cur is not None:
        cur["lines"].append(s)

entries = [{
    "slug": "gyeoulsae",
    "title": meta["title"],
    "year": meta["year"],
    "outlet": meta["outlet"],
    "award": meta["award"],
    "stanzas": stanzas,
    "credit": credit,
}]

DATA = json.dumps({"writing": entries}, ensure_ascii=False, indent=2)

html = open("_template.html", encoding="utf-8").read()
html = html.replace("/*__DATA__*/null", DATA)
open("index.html", "w", encoding="utf-8").write(html)
print("index.html written:", os.path.getsize("index.html"), "bytes")
print("연 수:", len(stanzas), "| 각 연 행수:", [len(s["lines"]) for s in stanzas])
print("크레딧:", credit[:40], "...")
