"""확장자의 재발견 — 인쇄본/전자책 빌드

pages/*.md 원고를 읽어 크라운판(176x248mm) 자체완결 HTML 한 권을 만든다.
폰트(Pretendard)와 조판 엔진(Paged.js)을 안에 넣으므로 인터넷 없이 열린다.
브라우저로 열면 페이지가 나뉘어 보이고, 인쇄(Ctrl+P)로 PDF를 저장한다.

사용법:
    python print/build.py              # 전체 책
    python print/build.py --only 02    # 특정 장만 (집필 중 확인용, 폰트 미포함으로 가볍게)

TOC.md의 순서와 제목을 그대로 따르므로, 새 장을 쓰고 TOC.md에 등록하면
이 스크립트가 자동으로 포함한다. 장을 추가할 때 손댈 곳은 없다.
"""

import argparse
import base64
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
ASSETS = ROOT / "assets"
PRINT = ROOT / "print"
BUILD_ASSETS = PRINT / "assets"


# ---------------------------------------------------------------- TOC 읽기

def read_toc():
    """TOC.md에서 (깊이, 제목, 파일경로) 목록을 순서대로 뽑는다."""
    entries = []
    for line in (ROOT / "TOC.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\s*)[*-]\s*\[(.+?)\]\((.+?)\)\s*$", line)
        if not m:
            continue
        indent, title, path = m.groups()
        entries.append((len(indent) // 2, title, ROOT / path))
    return entries


# ---------------------------------------------------------------- 마크다운 변환

def inline(text):
    """문단 안쪽 서식: 코드, 굵게, 링크."""
    out = []
    for i, part in enumerate(text.split("`")):
        if i % 2:                                   # 홀수 조각 = 백틱 안
            out.append(f"<code>{html.escape(part)}</code>")
        else:
            part = html.escape(part)
            part = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part)
            part = re.sub(r"\[(.+?)\]\((.+?)\)", r"<a href='\2'>\1</a>", part)
            out.append(part)
    return "".join(out)


def embed_image(src, page_path):
    """이미지를 data URI로 박아 넣어 파일 하나로 완결시킨다."""
    p = (page_path.parent / src).resolve()
    if not p.exists():
        print(f"  ! 이미지 없음: {src}", file=sys.stderr)
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def convert(md, page_path):
    """이 책이 쓰는 마크다운 부분집합만 처리한다."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]

        # 코드 블록
        if line.startswith("```"):
            lang = line[3:].strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            cls = f" class='lang-{lang}'" if lang else ""
            out.append(f"<pre{cls}><code>{html.escape(chr(10).join(body))}</code></pre>")
            continue

        # TIP 박스
        m = re.match(r'^\[\[TIP\("(.+?)"\)\]\]\s*$', line)
        if m:
            title, body, i = m.group(1), [], i + 1
            while i < len(lines) and not lines[i].startswith("[[/TIP]]"):
                body.append(lines[i])
                i += 1
            i += 1
            inner = convert("\n".join(body), page_path)
            out.append(
                f"<aside class='tip'><p class='tip-title'>{inline(title)}</p>{inner}</aside>"
            )
            continue

        # 표
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            head = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tb = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>")
            continue

        # 그림 (단독 줄)
        m = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", line)
        if m:
            alt, src = m.groups()
            uri = embed_image(src, page_path)
            cap = ""
            if i + 2 < len(lines) and lines[i + 2].startswith("*") and lines[i + 2].endswith("*"):
                cap = f"<figcaption>{inline(lines[i + 2].strip('*'))}</figcaption>"
                i += 2
            out.append(f"<figure><img alt='{html.escape(alt)}' src='{uri}'>{cap}</figure>")
            i += 1
            continue

        # 제목
        if line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
            i += 1
            continue
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
            i += 1
            continue

        # 목록
        if re.match(r"^\d+\.\s", line) or line.startswith("- "):
            ordered = bool(re.match(r"^\d+\.\s", line))
            items = []
            while i < len(lines) and (re.match(r"^\d+\.\s", lines[i]) or lines[i].startswith("- ")):
                items.append(re.sub(r"^(\d+\.|-)\s+", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            continue

        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue

        if not line.strip():
            i += 1
            continue

        # 문단 (빈 줄까지 이어 붙인다)
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#|\||```|!\[|\[\[|- |\d+\.\s|---$)", lines[i]
        ):
            para.append(lines[i])
            i += 1
        text = " ".join(para)
        cls = " class='next'" if text.startswith("**다음 장") else ""
        out.append(f"<p{cls}>{inline(text)}</p>")

    return "\n".join(out)


# ---------------------------------------------------------------- 조판

CSS = """
@page {
  size: 176mm 248mm;
  margin: 20mm 18mm 20mm 18mm;
  @bottom-center { content: counter(page); font-family:"Pretendard"; font-size:8.5pt; color:#8a8184; }
}
@page:first { @bottom-center { content: none; } }
@page cover { margin: 0; @bottom-center { content: none; } }

:root{ --ink:#2B2728; --accent:#7A4A5C; --muted:#756D70; --rule:#d9cfc7; --paper:#F5EFE7; }

*{ box-sizing:border-box; }
html{ font-size: 10.4pt; }
body{
  margin:0; color:var(--ink); background:#fff;
  font-family:"Pretendard", -apple-system, system-ui, sans-serif;
  line-height:1.72; letter-spacing:-.003em; word-break:keep-all;
  hanging-punctuation: allow-end;
}

/* 표지 */
.cover{ page: cover; break-after:page; }
.cover img{ width:176mm; height:248mm; object-fit:cover; display:block; }

/* 장 시작 */
.chapter{ break-before:page; }
.chapter h1{
  font-weight:800; font-size:1.72rem; line-height:1.3; letter-spacing:-.02em;
  margin:6mm 0 8mm; padding-bottom:5mm; border-bottom:2px solid var(--accent);
  string-set: runhead content();
}
.front h1{ border-bottom:1px solid var(--rule); }
h2{
  font-weight:700; font-size:1.16rem; line-height:1.4; margin:9mm 0 3mm;
  color:var(--accent); break-after:avoid;
}
h2 + p{ break-before:avoid; }

p{ margin:0 0 .9em; text-align:justify; }
p.next{ margin-top:8mm; padding-top:4mm; border-top:1px solid var(--rule); color:var(--muted); }
strong{ font-weight:700; }
a{ color:inherit; text-decoration:none; border-bottom:1px solid var(--rule); }
code{
  font-family: ui-monospace, "Cascadia Mono", Consolas, monospace;
  font-size:.86em; background:#f2ece6; padding:.08em .34em; border-radius:3px;
  word-break:break-all;
}

/* 표 */
table{ width:100%; border-collapse:collapse; margin:5mm 0; font-size:.9rem; break-inside:avoid; }
th,td{ text-align:left; padding:2.4mm 3mm; vertical-align:top; line-height:1.55; }
thead th{ border-bottom:1.4px solid var(--ink); font-size:.82rem; color:var(--muted); font-weight:700; }
tbody tr{ border-bottom:1px solid var(--rule); }
tbody tr:nth-child(odd){ background:rgba(122,74,92,.04); }

/* 코드 */
pre{
  background:#2B2728; color:#f3ede4; border-radius:5px;
  padding:4mm 5mm; margin:4mm 0; overflow:hidden;
  font-size:.82rem; line-height:1.6; white-space:pre-wrap; word-break:break-all;
  break-inside:avoid;
}
pre code{ background:none; color:inherit; padding:0; font-size:1em; }

/* 실습 박스 */
.tip{
  background:var(--paper); border:1px solid var(--rule); border-left:3px solid var(--accent);
  border-radius:4px; padding:5mm 6mm 4mm; margin:5mm 0; break-inside:avoid;
}
.tip .tip-title{ font-weight:800; color:var(--accent); margin:0 0 3mm; font-size:.98rem; }
.tip p{ text-align:left; }
.tip ol, .tip ul{ margin:0 0 3mm; padding-left:5mm; }
.tip li{ margin-bottom:1.6mm; }

/* 그림 */
figure{ margin:6mm 0; break-inside:avoid; }
figure img{ width:100%; height:auto; display:block; }
figcaption{ font-size:.84rem; color:var(--muted); margin-top:3mm; text-align:center; line-height:1.55; }

ol,ul{ margin:0 0 .9em; padding-left:6mm; }
li{ margin-bottom:1.2mm; }
hr{ border:none; border-top:1px solid var(--rule); margin:6mm 0; }
"""


def build(only=None):
    entries = read_toc()
    if only:
        entries = [e for e in entries if e[2].name.startswith(only)]
        if not entries:
            sys.exit(f"'{only}'로 시작하는 페이지가 TOC.md에 없습니다.")

    parts = []

    cover = ASSETS / "cover.png"
    if cover.exists() and not only:
        b64 = base64.b64encode(cover.read_bytes()).decode()
        parts.append(f"<section class='cover'><img src='data:image/png;base64,{b64}' alt='표지'></section>")

    for _, title, path in entries:
        if not path.exists():
            print(f"  ! 원고 없음: {path}", file=sys.stderr)
            continue
        body = convert(path.read_text(encoding="utf-8"), path)
        front = "front" if path.stem.startswith("00") or "part" in path.stem else ""
        parts.append(f"<section class='chapter {front}'>{body}</section>")
        print(f"  · {title}")

    font_css = ""
    font = BUILD_ASSETS / "Pretendard.woff2"
    if font.exists() and not only:
        b64 = base64.b64encode(font.read_bytes()).decode()
        font_css = (
            '@font-face{font-family:"Pretendard";font-style:normal;font-weight:45 920;'
            f'font-display:block;src:url("data:font/woff2;base64,{b64}") format("woff2");}}'
        )

    paged = ""
    pjs = BUILD_ASSETS / "paged.polyfill.js"
    if pjs.exists():
        paged = f"<script>{pjs.read_text(encoding='utf-8')}</script>"

    title = "확장자의 재발견" + (f" — {only}장" if only else "")
    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{font_css}{CSS}</style>
</head>
<body>
{chr(10).join(parts)}
{paged}
</body>
</html>"""

    name = f"확장자의재발견-{only}장-미리보기.html" if only else "확장자의재발견-크라운판.html"
    out = PRINT / name
    out.write_text(doc, encoding="utf-8")
    mb = out.stat().st_size / 1024 / 1024
    print(f"\n완료: print/{name}  ({mb:.1f} MB)")
    return out


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def to_pdf(html_path):
    """Paged.js 조판이 끝난 뒤에 PDF로 저장한다.

    헤드리스 Chrome의 --print-to-pdf를 그냥 쓰면 조판이 끝나기 전에 인쇄해
    앞부분 몇 쪽만 나온다. 그래서 쪽 수가 더 이상 늘지 않을 때까지 기다린다.
    """
    from playwright.sync_api import sync_playwright

    exe = next((p for p in CHROME_CANDIDATES if Path(p).exists()), None)
    pdf_path = html_path.with_suffix(".pdf")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=exe)
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="load", timeout=180_000)

        stable, last = 0, -1
        for _ in range(240):                       # 최대 2분
            n = page.evaluate("document.querySelectorAll('.pagedjs_page').length")
            stable = stable + 1 if n == last and n > 0 else 0
            last = n
            if stable >= 6:                        # 3초간 변화 없음 = 조판 완료
                break
            page.wait_for_timeout(500)
        print(f"  조판 완료: {last}쪽")

        page.pdf(path=str(pdf_path), prefer_css_page_size=True,
                 print_background=True, margin={"top": "0", "bottom": "0",
                                                "left": "0", "right": "0"})
        browser.close()

    mb = pdf_path.stat().st_size / 1024 / 1024
    print(f"완료: print/{pdf_path.name}  ({mb:.1f} MB)")
    return pdf_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="특정 장만 빌드 (예: 02)")
    ap.add_argument("--pdf", action="store_true", help="PDF까지 생성")
    args = ap.parse_args()
    out = build(args.only)
    if args.pdf:
        to_pdf(out)
