# CLAUDE.md — 이 저장소에서 Claude Code가 따를 지침

## 이 저장소가 하는 일
비개발자용 실용 교양서 **『확장자의 재발견』**의 원고 저장소다. 낯선 파일 확장자를 하나씩 열어 정체를 밝히고, 그 구조로 **무엇을 자동화할 수 있는지**, 그 일을 **AI에게 어떻게 시키는지**까지 다룬다. (자매편: 『브라우저의 재발견』)

이 저장소는 위키독스와 연동된다: **`main`에 push하면 위키독스 책에 자동 반영**된다. 규칙은 [github-wikidocs](https://github.com/pahkey/github-wikidocs)를 따른다.

## 저장소 구조 · 규칙
- `TOC.md` — 목차(위키독스 페이지 계층). 모든 페이지를 여기 등록해야 노출됨. `*` 리스트 + 2칸 들여쓰기, 제목은 페이지 H1과 정확히 일치.
- `pages/NN-slug.md` — 각 장. 번호 접두사 + kebab-case. H1은 `# NN. 제목`.
- `assets/` — 이미지. 페이지에서 `../assets/파일.png`로 참조(현재 검증된 경로).
- 상세 작성 규칙은 `AGENTS.md` 참고(제목/리스트/코드블록/이미지 규약).
- 위키독스 박스는 `[[TIP("제목")]] … [[/TIP]]`만 안전하게 지원됨. 그 외 콜아웃은 인용문/표로.

## 책의 톤·챕터 템플릿 (모든 장 공통)
- 대상: **비개발자**, 각 장에 **직접 해보는 실습** 포함. 문체 합니다체, 짧은 문장, 비유로 원리 대체 금지, **한계(보장하지 않는 것) 명시**.
- 각 장 4단 구성: ① 마주친 장면+정의(+신상명세 표) ② 해부(구조 도식+내부 파일 표+[손으로 해보기]) ③ **무엇을 자동화하나**(사람 vs 구조 비교표+지켜야 할 규칙) ④ **AI에게 시키는 법**(대화형 프롬프트+코딩도구 지시문)→한계→친척 포맷 확장→3줄 요약+다음 장 질문.
- 기준 구현: `pages/01-hwpx.md`. 새 장은 이 구조를 그대로 따른다.

## 100개 확장자 4개 부(部) 계획
1. 숨은 정체가 반전인 것: hwpx, docx, xlsx, pptx, epub, apk, jar, ipa (=ZIP+XML/묶음)
2. 일상에서 마주치는 낯선 것: svg, md, yaml, toml, ics, vcf, torrent, iso, csv
3. AI·데이터 시대 포맷: json, jsonl, parquet, gguf, safetensors, ipynb, webp, avif
4. 미디어·창작 포맷: heic, raw(cr2/nef), flac, webm, gltf/glb, psd

## 진행 상태
- [x] 01. HWPX (pages/01-hwpx.md, assets/hwpx-structure.png)
- [ ] **다음: 02. XML** — 01의 마지막 질문("그 <태그>들의 정체가 XML")에서 이어짐. 제목안: `02. XML — 브라우저에 숨어 있던 만능 번역기`
- [ ] 이후 03. SVG, 04. JSON, 05. CSV …

## 처음 한 번: GitHub에 올리고 위키독스에 연결
```bash
# (이 폴더에서) GitHub CLI 인증이 안 돼 있으면 먼저:
gh auth login

# 저장소 생성 + 첫 push 한 번에 (공개 권장)
git init && git add . && git commit -m "docs: 확장자의 재발견 — 01. HWPX"
git branch -M main
gh repo create hwakjangja-book --public --source=. --remote=origin --push
```
그다음 위키독스 → **새 책 만들기 → 깃허브 연동**에서 이 저장소를 연결하면 끝.

## 새 장 추가 워크플로우 (반복)
1. `pages/NN-slug.md` 작성(H1 `# NN. 제목`), 필요 그림은 `assets/`에.
2. `TOC.md`에 한 줄 추가(위치 맞게).
3. 커밋 후 push → 위키독스 자동 반영.
```bash
git add . && git commit -m "docs: add ch NN. 제목" && git push
```

## 참고: 인쇄용 책(별도 산출물)
위키독스와 별개로, 인쇄판은 **크라운판 176×248mm, 대칭 여백**, Pretendard 내장 자체완결 HTML → PDF(3mm 블리드+재단선) 파이프라인으로 만든다. 원고는 동일하되 조판만 다르다.
