# VERTICAL_SLICE_PLAN.md

# Business OS — План первого вертикального среза

**Версия:** 1.0  
**Статус:** READY FOR IMPLEMENTATION

---

## 1. Цель среза

Создать минимальный работающий путь через все ключевые слои Business OS.

На этом этапе качество функций может быть базовым, но архитектурные границы должны быть реальными.

---

## 2. Демонстрационный сценарий

### Вход

**Документ:**

> Менеджер по продажам обязан связаться с новым лидом не позднее 15 минут после его создания.

**CRM-событие:**

```json
{
  "lead_id": "L-1001",
  "created_at": "2026-08-01T09:00:00+03:00",
  "first_contact_at": "2026-08-01T09:47:00+03:00",
  "assigned_position": "Sales Manager",
  "actual_actor": "employee-17"
}
```

### Ожидаемый результат

- нормативный срок: 15 минут;
- фактический срок: 47 минут;
- отклонение: 32 минуты;
- статус: существенное расхождение;
- доказательства доступны;
- владелец подтверждает;
- создается Knowledge Record;
- AI формирует осторожную рекомендацию;
- руководитель сохраняет решение.

---

## 3. Срез 0 — Технический каркас

Создать:

- monorepo;
- `apps/web`;
- `apps/api`;
- `apps/worker`;
- PostgreSQL;
- MinIO;
- Redis;
- миграции;
- health checks;
- базовый audit;
- `.env.example`;
- Docker Compose;
- CI: lint, typecheck, tests.

---

## 4. Срез 1 — Минимальная модель

Создать сущности:

- Company;
- User;
- Role;
- Department;
- Source;
- Document;
- DocumentVersion;
- DocumentFragment;
- ExtractedStatement;
- RawRecord;
- ObservedFact;
- DataQualityIssue;
- AlignmentCheck;
- AlignmentIssue;
- KnowledgeRecord;
- AIAnalysis;
- Recommendation;
- Decision;
- AuditEvent.

---

## 5. Срез 2 — Документ

Пользователь должен:

1. загрузить PDF;
2. увидеть оригинал;
3. создать DocumentVersion;
4. получить один DocumentFragment;
5. получить ExtractedStatement типа `deadline`;
6. подтвердить утверждение;
7. открыть источник.

На первом срезе допустим:

- mock extraction;
- ручной ввод структурированного утверждения.

Нельзя откладывать модель source anchors.

---

## 6. Срез 3 — Фактическая запись

Пользователь должен:

1. зарегистрировать CRM как Source;
2. импортировать одну JSON/CSV-запись;
3. увидеть RawRecord;
4. получить нормализованный ObservedFact;
5. открыть lineage;
6. повторно импортировать запись без дубля.

---

## 7. Срез 4 — Data Quality

Правила:

- `created_at` обязателен;
- `first_contact_at` обязателен;
- `first_contact_at >= created_at`;
- источник не должен быть stale;
- lead ID обязателен.

При ошибке:

- создается DataQualityIssue;
- запись получает статус quarantine;
- анализ блокируется;
- Data Doctor AI может сформировать объяснение.

---

## 8. Срез 5 — Reality Alignment

Comparison rule:

```text
actual_first_contact_minutes
    =
first_contact_at - created_at
```

Условие:

```text
actual_first_contact_minutes > normative_deadline_minutes
```

Результат:

- норматив;
- факт;
- отклонение;
- severity;
- evidence;
- Trust;
- owner;
- status.

---

## 9. Срез 6 — Подтверждение

Владелец может:

- подтвердить расхождение;
- отклонить;
- запросить данные;
- принять временное отклонение.

После подтверждения создается Knowledge Record.

До подтверждения AI видит элемент как `unverified evidence`.

---

## 10. Срез 7 — AI-анализ

Вопрос:

> Есть ли подтвержденное нарушение срока обработки лида L-1001 и что можно сделать?

Context Builder передает:

- подтвержденное нормативное знание;
- Observed Fact;
- Alignment Evidence;
- Trust;
- ссылки на источники;
- ограничения.

Structured output:

```json
{
  "facts": [],
  "observations": [],
  "hypotheses": [],
  "recommendations": [],
  "missing_data": [],
  "sources": [],
  "trust_index": 0,
  "blocked": false
}
```

---

## 11. Срез 8 — Решение

Руководитель может:

- принять;
- изменить;
- отклонить;
- назначить ответственного;
- установить дату контроля;
- указать ожидаемый результат.

---

## 12. Срез 9 — Контроль результата

Пользователь вводит:

- новое фактическое значение;
- дату проверки;
- комментарий.

Система показывает:

- исходный факт;
- ожидаемый результат;
- фактический результат;
- отклонение;
- статус решения.

---

## 13. Минимальные API

```text
POST   /api/v1/documents
GET    /api/v1/documents/{id}
POST   /api/v1/documents/{id}/statements
POST   /api/v1/statements/{id}/confirm

POST   /api/v1/sources
POST   /api/v1/ingestion/import
GET    /api/v1/raw-records/{id}
GET    /api/v1/facts/{id}

POST   /api/v1/alignment/checks
GET    /api/v1/alignment/issues/{id}
POST   /api/v1/alignment/issues/{id}/confirm

GET    /api/v1/knowledge/{id}

POST   /api/v1/analyses
GET    /api/v1/analyses/{id}

POST   /api/v1/decisions
POST   /api/v1/decisions/{id}/result
```

---

## 14. Минимальные экраны

- Login;
- Readiness Dashboard;
- Document Upload;
- Document Card;
- Statement Review;
- Source Import;
- Data Quality Issue;
- Alignment Issue;
- Analysis;
- Evidence Panel;
- Decision;
- Decision Result.

---

## 15. Обязательные тесты

- повторная загрузка документа;
- версия не перезаписывается;
- source anchor существует;
- повторный импорт не создает дубль;
- некорректная дата блокирует анализ;
- stale source блокирует анализ;
- неподтвержденное утверждение не становится знанием;
- конфликт виден;
- AI output проходит schema validation;
- AI не получает закрытые данные;
- missing data останавливает анализ;
- решение записывается в audit;
- результат решения сравнивается с ожиданием.

---

## 16. Definition of Done вертикального среза

Срез завершен, если:

- весь сценарий проходит через UI;
- нет прямой записи AI в Knowledge Base;
- каждый критический элемент имеет источник;
- блокировки воспроизводимы;
- права проверяются;
- audit содержит полный путь;
- состояние можно развернуть локально одной командой;
- demo-сценарий воспроизводим.
