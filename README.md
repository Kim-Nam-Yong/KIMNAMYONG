# KIMNAMYONG

김남용 개인 포트폴리오. **일 / 글 / 삶** 세 개 섹션.

- 배포: https://kimnamyong.vercel.app
- 컨셉: 백지 한가운데 텍스트만. 화면에 상시 노출되는 UI를 최소화한다.

## 구조

```
index.html            배포되는 산출물 — 빌드 결과이므로 직접 고치지 않는다
_template.html        실제 소스. CSS와 JS는 여기서 고친다
build_site.py         원고(MDX) + 템플릿 → index.html
글/*.mdx              「글」 원고
일/                   「일」 원고 (예정)
KIMNAMYONG_기획서.md   화면 설계 문서
```

`index.html`은 빌드 산출물이다. **직접 수정하면 다음 빌드에서 덮어써진다.**
스타일과 동작은 `_template.html`, 원고는 `글/`에서 고친다.

## 원고 추가

`글/`에 `.mdx` 파일을 만든다.

```yaml
---
title: 제목
year: 2026
category: 에세이        # 에세이 | UX라이팅 | 카피
outlet: 매체·클라이언트   # 선택
award: 수상             # 선택
---

본문
```

## 빌드 · 배포

```bash
python3 build_site.py
```

`main`에 push하면 Vercel이 자동 배포한다.
`.vercelignore`가 원고와 소스를 배포 번들에서 제외하므로, 사이트로 서빙되는 파일은 `index.html`뿐이다.

## 화면 동작

| 상황 | 동작 |
|---|---|
| 긴 글 | 스크롤바 없이 18px/s로 자동 롤링 → 끝나면 처음 위치로 복귀 후 고정 |
| 짧은 글 | 화면 정가운데 고정 |
| 글 목록 | 데스크톱은 마우스를 화면 왼쪽 끝까지, 모바일은 좌측 스와이프 또는 좌상단 버튼 |
| GNB | 3초 무동작 시 사라지고, 마우스를 움직이면 복귀 |

사용자가 휠이나 터치로 스크롤하면 자동 롤링을 멈추고 제어권을 넘긴다.
`prefers-reduced-motion` 환경에서는 롤링 없이 일반 스크롤로 동작한다.

주요 튜닝값은 `_template.html`의 `ROLL_SPEED`, `START_HOLD`, `END_HOLD`,
`RETURN_MS`, `OPEN_X`, `CLOSE_X` 상수에 모여 있다.
