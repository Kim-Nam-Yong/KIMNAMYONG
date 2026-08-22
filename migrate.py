# -*- coding: utf-8 -*-
"""워드프레스 내보내기(WXR) → MDX + WebP 이미지

사용법:
    python3 migrate.py <export.xml> [글ID ...]
    인자로 ID를 주면 그 글만, 없으면 CLASSIFY 에 있는 전부를 옮긴다.
"""
import xml.etree.ElementTree as ET
import re, os, sys, html, json, urllib.request, unicodedata

NS = {'wp': 'http://wordpress.org/export/1.2/',
      'content': 'http://purl.org/rss/1.0/modules/content/'}
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
DISPLAY_W = 900
SECTION_DIR = {'일': '일', '글': '글', '삶': '삶'}          # 원고(소스) 폴더 — 배포 제외라 한글 가능
SECTION_WEB = {'일': 'work', '글': 'writing', '삶': 'life'}   # 웹 경로 — Vercel 이 한글 경로를 서빙하지 못한다

g = lambda i, t: i.findtext(t, '', NS)


# ── 첨부 색인 ────────────────────────────────────────────
def base_key(u):
    n = os.path.basename(u)
    return re.sub(r'-\d+x\d+(?=\.[a-z]+$)', '', n, flags=re.I).lower()


def build_attachment_index(items):
    idx = {}
    for i in items:
        if g(i, 'wp:post_type') == 'attachment':
            u = g(i, 'wp:attachment_url')
            if u:
                idx[base_key(u)] = u
    return idx


# ── 본문 → 블록 ──────────────────────────────────────────
def img_url(tag):
    """lazy-load 된 경우 data-src 에 진짜 주소가 있다."""
    for a in ('data-src', 'src'):
        m = re.search(a + r'="([^"]+)"', tag)
        if m and not m.group(1).startswith('data:'):
            return m.group(1)
    return None


def to_blocks(body, resolve):
    """resolve(url) → 로컬 경로 또는 None"""
    def repl(m):
        u = img_url(m.group(0))
        local = resolve(u) if u else None
        return f'\n\n@@IMG:{local}@@\n\n' if local else '\n\n'

    s = re.sub(r'<img[^>]*>', repl, body)
    s = re.sub(r'<figcaption[^>]*>.*?</figcaption>', '', s, flags=re.S | re.I)
    s = re.sub(r'<h([1-6])[^>]*>', '\n\n@@H@@', s)
    s = re.sub(r'</h[1-6]>', '\n\n', s)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'</(p|div|li)>', '\n\n', s)
    s = re.sub(r'<li[^>]*>', '· ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace(' ', ' ')

    out, prev_blank = [], False
    for line in (l.strip() for l in s.split('\n')):
        if not line:
            if not prev_blank:
                out.append('')
            prev_blank = True
        else:
            out.append(line)
            prev_blank = False
    return [c.strip() for c in '\n'.join(out).strip().split('\n\n') if c.strip()]


# ── 이미지 내려받기 · 변환 ───────────────────────────────
def fetch_and_convert(url, orig_dir, out_dir, stem):
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(url)[1].split('?')[0].lower() or '.jpg'
    orig = os.path.join(orig_dir, stem + ext)

    if not os.path.exists(orig):
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=60).read()
        if len(data) < 500:
            raise ValueError(f'too small ({len(data)}B)')
        open(orig, 'wb').write(data)

    from PIL import Image
    im = Image.open(orig)
    im = im.convert('RGBA') if im.mode in ('RGBA', 'LA', 'P') else im.convert('RGB')
    if im.mode == 'RGBA':
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    ow, oh = im.size
    for label, target in (('', DISPLAY_W), ('@2x', min(DISPLAY_W * 2, ow))):
        w = min(target, ow)
        h = max(1, round(oh * w / ow))
        im.resize((w, h), Image.LANCZOS).save(
            os.path.join(out_dir, f'{stem}{label}.webp'), 'WEBP', quality=82, method=6)
    return ow, oh


# ── 한 편 이관 ───────────────────────────────────────────
def migrate_post(item, section, att_idx, report, label=''):
    pid = g(item, 'wp:post_id')
    title = (item.findtext('title') or '').strip()
    date = g(item, 'wp:post_date')[:10]
    year = date[:4]
    slug = f'p{pid}'
    body = g(item, 'content:encoded')

    img_dir = f'images/{SECTION_WEB[section]}/{slug}'
    org_dir = f'originals/{SECTION_WEB[section]}/{slug}'
    seen, failures = {}, []

    def resolve(u):
        key = base_key(u)
        real = att_idx.get(key)
        if not real:
            failures.append(('매핑없음', os.path.basename(u)))
            return None
        if key in seen:
            return seen[key]
        stem = f'{len(seen) + 1:02d}'
        try:
            fetch_and_convert(real, org_dir, img_dir, stem)
        except Exception as e:
            failures.append((type(e).__name__, os.path.basename(real)))
            return None
        path = f'/{img_dir}/{stem}.webp'
        seen[key] = path
        return path

    blocks = to_blocks(body, resolve)

    lines, img_n = [], 0
    for b in blocks:
        if b.startswith('@@IMG:'):
            img_n += 1
            payload = b.replace('@@IMG:', '').replace('@@', '').strip()
            src, _, alt = payload.partition('|')
            # 원본에 alt 가 거의 없다(첨부 459개 중 0개). 없으면 제목 기반으로 만든다.
            if not alt:
                alt = f'{title} — 이미지 {img_n}'
            lines.append(f'![{alt}]({src})')
        elif b.startswith('@@H@@'):
            h = b.replace('@@H@@', '').strip()
            if h:
                lines.append('## ' + h)
        else:
            lines.append(b)

    fm = (f'---\ntitle: {title}\nlabel: {label or title}\nyear: {year}\ndate: {date}\n'
          f'section: {section}\nsource: http://www.bookdodook.com/?p={pid}\n---\n\n')
    path = f'{SECTION_DIR[section]}/{slug}.mdx'
    os.makedirs(SECTION_DIR[section], exist_ok=True)
    open(path, 'w', encoding='utf-8').write(fm + '\n\n'.join(lines) + '\n')

    text_len = sum(len(l) for l in lines if not l.startswith('!['))
    report.append({'pid': pid, 'title': title, 'section': section, 'path': path,
                   'chars': text_len, 'images': len(seen), 'failures': failures})


# ── 실행 ─────────────────────────────────────────────────
if __name__ == '__main__':
    xml_path = sys.argv[1]
    want = set(sys.argv[2:])
    classify = json.load(open('분류.json', encoding='utf-8')) if os.path.exists('분류.json') else {}

    items = ET.parse(xml_path).getroot().find('channel').findall('item')
    att_idx = build_attachment_index(items)
    print(f'첨부 색인 {len(att_idx)}개')

    report = []
    for it in items:
        if g(it, 'wp:post_type') != 'post' or g(it, 'wp:status') != 'publish':
            continue
        pid = g(it, 'wp:post_id')
        if want and pid not in want:
            continue
        entry = classify.get(pid) or {}
        section = entry.get('section', '일')
        label = entry.get('label', '')
        print(f'  p{pid} … ', end='', flush=True)
        migrate_post(it, section, att_idx, report, label)
        r = report[-1]
        print(f'{r["section"]} / {r["chars"]}자 / 이미지 {r["images"]}개'
              + (f' / 실패 {len(r["failures"])}' if r['failures'] else ''))

    print(f'\n총 {len(report)}편')
    bad = [r for r in report if r['failures']]
    if bad:
        print('실패 목록:')
        for r in bad:
            for kind, name in r['failures']:
                print(f'  p{r["pid"]}  {kind}  {name}')
    else:
        print('이미지 실패 0건')
