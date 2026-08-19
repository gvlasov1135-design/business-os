# Реальные данные — пилот Бистро

Положите Excel в `data/pilot/bistro_2026.xlsx` (уже скопирован из Downloads).

Файл — **сводная финмодель** (не CRM-лиды):

| Лист | Система (logical) |
|------|-------------------|
| Отчет о фин.рез. / Расходы / баланс | 1C |
| Деление БарКухня | RKeeper |
| Аналитическая форма | Storyhouse |

## UI

1. http://localhost:3010/login  
2. http://localhost:3010/pilot — загрузить xlsx → «Запустить первый анализ»  
3. `/analysis` · `/council` · `/executive`

## CLI

```bash
bash scripts/pilot_bistro.sh
# или
bash scripts/pilot_bistro.sh "/path/to/Бистро 2026.xlsx"
```

API: `POST /api/v1/pilot/bistro/run` (multipart `file`, optional `company_id`, `question`).
