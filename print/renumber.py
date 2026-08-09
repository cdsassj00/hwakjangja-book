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
    changed = [c for c in chapters if c["old_no"] != c["new_no"]]

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

    # 1) 파일 이름 바꾸기 — git 이력을 잇기 위해 git mv 를 쓴다
    for c in changed:
        subprocess.run(["git", "-C", str(ROOT), "mv", str(c["old_path"].relative_to(ROOT)),
                        str(c["new_path"].relative_to(ROOT))], check=True)

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

    # 4) 사람이 손봐야 할 곳 알려주기
    print("\n--- 손으로 고쳐야 하는 연결 문장 ---")
    for p in sorted((ROOT / "pages").glob("[0-9][0-9]-*.md")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "다음 장 →" in line:
                print(f"  {p.name}:{n}  {line.strip()[:70]}")
    print("\n위 줄들이 새 순서와 맞는지 확인하고, 다음 장 도입부의 연결 문장도 함께 보세요.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 바꾼다")
    main(ap.parse_args().apply)
