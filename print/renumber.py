"""장 번호 다시 매기기 — 중간에 새 장을 끼워 넣을 때 쓴다.

TOC.md의 순서를 정답으로 보고, pages/ 의 파일명 번호와 각 파일 H1의 번호를
그 순서에 맞춘다. TOC.md의 링크 경로와 제목 번호도 함께 고친다.

사람이 직접 손봐야 하는 곳(장 끝의 "다음 장 →" 줄과 다음 장 도입부의 연결
문장)은 고치지 않고 목록으로만 알려 준다. 그 문장들은 내용이라서 기계가
바꿀 수 없기 때문이다.

사용법:
    python print/renumber.py            # 무엇이 바뀔지 보여주기만 한다
    python print/renumber.py --apply    # 실제로 바꾼다

새 장을 끼워 넣는 순서:
    1. pages/ 에 원고를 아무 번호로나 만든다 (예: 99-zip.md)
    2. TOC.md 의 원하는 자리에 줄을 추가한다
    3. 이 스크립트를 --apply 로 실행한다
    4. 스크립트가 알려 준 "다음 장" 연결 문장들을 손으로 고친다
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOC = ROOT / "TOC.md"

# "* [12. HEIC — ...](pages/12-heic.md)" 형태에서 번호가 붙은 장만 대상으로 삼는다.
ENTRY = re.compile(r"^(\s*)([*-])\s*\[(\d+)\.\s*(.+?)\]\((pages/.+?)\)\s*$")


def plan():
    lines = TOC.read_text(encoding="utf-8").splitlines()
    chapters, seq = [], 0
    for i, line in enumerate(lines):
        m = ENTRY.match(line)
        if not m:
            continue
        seq += 1
        indent, bullet, old_no, title, path = m.groups()
        old_path = ROOT / path
        slug = re.sub(r"^\d+-", "", old_path.name)
        new_name = f"{seq:02d}-{slug}"
        chapters.append({
            "line": i, "indent": indent, "bullet": bullet,
            "old_no": int(old_no), "new_no": seq, "title": title,
            "old_path": old_path, "new_path": old_path.parent / new_name,
        })
    return lines, chapters


def main(apply):
    lines, chapters = plan()
    # 이름을 바꿔야 하는지는 '파일 이름'을 기준으로 판단한다.
    # 목차 제목의 번호만 보면, 새로 넣은 원고(98-odf.md 처럼 임시 번호를 단 것)를
    # 놓친다.
    changed = [c for c in chapters if c["old_path"].name != c["new_path"].name]

    if not changed:
        print("번호가 이미 TOC.md 순서와 맞습니다. 바꿀 것이 없습니다.")
    else:
        print("바뀔 장:")
        for c in changed:
            print(f"  {c['old_no']:02d} → {c['new_no']:02d}  {c['title']}")
            print(f"       {c['old_path'].name} → {c['new_path'].name}")

    missing = [c for c in chapters if not c["old_path"].exists()]
    for c in missing:
        print(f"  ! 원고 없음: {c['old_path'].name}")
    if missing:
        sys.exit("원고를 먼저 만들어 주세요.")

    if not apply:
        print("\n(미리보기입니다. 실제로 바꾸려면 --apply 를 붙이세요)")
        return

    # 1) 파일 이름 바꾸기
    #    이미 커밋된 원고는 git mv 로 옮겨 이력을 잇는다.
    #    아직 커밋되지 않은 새 원고는 git 이 모르므로 그냥 이름만 바꾼다.
    for c in changed:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "mv", str(c["old_path"].relative_to(ROOT)),
             str(c["new_path"].relative_to(ROOT))],
            capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if r.returncode != 0:
            c["old_path"].rename(c["new_path"])
            print(f"  (새 원고라 git 이력 없이 이름만 바꿈: {c['new_path'].name})")

    # 2) 각 원고의 H1 번호 고치기
    for c in chapters:
        p = c["new_path"]
        text = p.read_text(encoding="utf-8")
        fixed = re.sub(r"^#\s*\d+\.\s*", f"# {c['new_no']:02d}. ", text, count=1)
        if fixed != text:
            p.write_text(fixed, encoding="utf-8")

    # 3) TOC.md 다시 쓰기
    for c in chapters:
        rel = c["new_path"].relative_to(ROOT).as_posix()
        lines[c["line"]] = f"{c['indent']}{c['bullet']} [{c['new_no']:02d}. {c['title']}]({rel})"
    TOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n파일명·H1·TOC.md 를 맞췄습니다.")

    # 4) "다음 장 →" 줄의 번호 맞추기
    #    제목은 그대로이므로 제목으로 새 번호를 찾아 붙인다.
    by_title = {c["title"]: c["new_no"] for c in chapters}
    NEXT = re.compile(r"(\*\*다음 장 →\*\*\s*\*\*)(\d+)\.\s*(.+?)(\*\*)")
    fixed_lines = []
    for p in sorted((ROOT / "pages").glob("[0-9][0-9]-*.md")):
        text = p.read_text(encoding="utf-8")

        def repl(m):
            title = m.group(3).strip()
            no = by_title.get(title)
            if no is None:
                fixed_lines.append(f"  ? {p.name}: 목차에 없는 제목 — {title}")
                return m.group(0)
            if int(m.group(2)) != no:
                fixed_lines.append(f"  · {p.name}: {m.group(2)} → {no:02d}  {title}")
            return f"{m.group(1)}{no:02d}. {title}{m.group(4)}"

        new = NEXT.sub(repl, text)
        if new != text:
            p.write_text(new, encoding="utf-8")

    if fixed_lines:
        print("\n--- '다음 장 →' 줄 번호를 맞췄습니다 ---")
        for l in fixed_lines:
            print(l)

    # 5) 사람이 손봐야 할 곳 알려주기
    print("\n--- 사람이 확인해야 하는 곳 ---")
    print("장 끝의 연결 문단과 다음 장 도입부의 문장은 내용이라서 기계가 못 고칩니다.")
    print("아래 장들의 마지막 문단과 그다음 장 첫 문단이 이어지는지 읽어 보세요.")
    for c in chapters:
        if c["old_no"] != c["new_no"]:
            print(f"  {c['new_path'].name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 바꾼다")
    main(ap.parse_args().apply)
