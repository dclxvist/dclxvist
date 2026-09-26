# Баннер профиля

- `about.md` — текст. Сверху в блоке `---` ник и статус, ниже обычный markdown: `## заголовок`, абзацы, списки `- `, `**жирный**`, `` `код` ``.
- `build.py` — собирает `profile-dark.svg` и `profile-light.svg`.
- `fonts/` — Noto Sans и Noto Sans Mono (лицензия OFL, `fonts/OFL.txt`).

## Как поменять текст

**Через GitHub (ничего ставить не нужно):** открой `banner/about.md`, нажми карандаш, поправь, закоммить. Workflow `.github/workflows/banner.yml` сам пересоберёт обе SVG и поднимет `?v=` в README.

**Локально:**

    pip install fonttools
    python banner/build.py

Потом закоммить обе SVG и подними `?v=` в README.

## Настройки в начале build.py

- `BURSTS` — моменты сбоев внутри цикла, `CYCLE` — длина цикла (сейчас сбой раз в ~8–9 с).
- `BURST_LEN` — длительность сбоя.
- `GLITCH_CHARS` — какими символами «ломаются» буквы.
