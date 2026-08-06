# IMPLEMENTATION_GUIDE.md

# Business OS — Руководство по реализации

**Версия:** 1.0  
**Статус:** базовое руководство  
**Назначение:** перевести продуктовые и технические спецификации Business OS в практический план разработки MVP в Cursor.

---

## 1. Цель документа

Этот документ определяет:

- с чего начинать разработку;
- как организовать репозиторий;
- какие компоненты создавать;
- в каком порядке реализовывать функции;
- какие технические решения принять для MVP;
- как проверять соответствие исходному ТЗ;
- как не превратить проект в бесконечную платформу;
- когда MVP можно считать готовым.

Главный ориентир:

> Business OS сначала приводит документацию и данные компании к проверяемому состоянию, затем сравнивает документы с реальной деятельностью и только после этого формирует рекомендации руководителю.

---

## 2. Главная граница MVP

MVP создается:

- для одной компании;
- как закрытая система;
- без multi-tenancy;
- без публичного SaaS;
- без marketplace;
- без собственной foundation model;
- без полной замены CRM, ERP и бухгалтерии;
- без автономных критических действий;
- без десятков интеграций;
- без сложной отраслевой универсализации.

MVP должен доказать один полный сценарий:

```text
Документ компании
        ↓
Извлеченные утверждения
        ↓
Фактические данные из одного источника
        ↓
Сравнение «как должно быть» и «как есть»
        ↓
Подтверждение владельцем
        ↓
Корпоративная база знаний
        ↓
Вопрос руководителя
        ↓
Доказательная рекомендация AI
        ↓
Решение и контроль результата
```

---

## 3. Документы, определяющие разработку

Источниками требований являются:

1. `VISION.md`
2. `TERMINOLOGY.md`
3. `DOCUMENT_INTELLIGENCE_SPEC.md`
4. `REALITY_ALIGNMENT_SPEC.md`
5. `DATA_INGESTION_SPEC.md`
6. `KNOWLEDGE_BASE_SPEC.md`
7. `AI_ANALYSIS_SPEC.md`
8. `EXECUTIVE_DASHBOARD_SPEC.md`
9. `CORE_SPEC.md`
10. `UI_UX_SPEC.md`
11. `IMPLEMENTATION_GUIDE.md`

При конфликте требований используется следующий приоритет:

```text
Исходная цель проекта
        ↓
VISION
        ↓
CORE_SPEC
        ↓
Специализированные спецификации
        ↓
IMPLEMENTATION_GUIDE
```

---

## 4. Рекомендуемый технологический стек MVP

### Frontend

- Next.js;
- TypeScript;
- React;
- TanStack Query;
- React Hook Form;
- Zod;
- компонентная библиотека с доступным исходным кодом;
- визуализация графов только там, где она нужна.

### Backend

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- Alembic;
- background workers.

### Основная база

- PostgreSQL.

### Векторный поиск

- pgvector.

### Полнотекстовый поиск

На первом этапе:

- PostgreSQL Full Text Search.

Позже при необходимости:

- OpenSearch.

### Файловое хранилище

- S3-compatible storage;
- локально — MinIO.

### Очереди и фоновые задачи

- Redis;
- Celery, Dramatiq или Arq.

Для MVP нужно выбрать один вариант и не менять без причины.

### Аутентификация

Один из вариантов:

- Keycloak;
- Auth0;
- корпоративный SSO;
- собственный auth только для локального прототипа.

### Наблюдаемость

- OpenTelemetry;
- Prometheus;
- Grafana;
- Sentry или аналог.

### Развертывание

На первом этапе:

- Docker;
- Docker Compose.

Kubernetes не нужен до появления реальной нагрузки и операционной необходимости.

---

## 5. Архитектурный стиль

Рекомендуемый подход для MVP:

> Модульный монолит с четкими доменными границами.

Не следует начинать с микросервисов.

Причины:

- одна команда;
- один продукт;
- быстрые изменения модели;
- меньше инфраструктурной сложности;
- проще транзакции;
- проще отладка;
- проще миграции.

Подсистемы проектируются как независимые модули, но разворачиваются единым backend-приложением.

---

## 6. Структура репозитория

Рекомендуемая структура:

```text
business-os/
├── apps/
│   ├── web/
│   ├── api/
│   └── worker/
├── packages/
│   ├── ui/
│   ├── shared-types/
│   ├── config/
│   └── sdk/
├── services/
│   ├── llm-gateway/
│   └── connector-runtime/
├── infrastructure/
│   ├── docker/
│   ├── migrations/
│   ├── monitoring/
│   └── scripts/
├── docs/
│   ├── specifications/
│   ├── architecture/
│   ├── decisions/
│   ├── api/
│   └── runbooks/
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   └── security/
├── .cursor/
│   ├── rules/
│   └── commands/
├── docker-compose.yml
├── Makefile
├── README.md
└── .env.example
```

---

## 7. Структура backend

```text
apps/api/src/
├── main.py
├── config/
├── common/
│   ├── auth/
│   ├── audit/
│   ├── events/
│   ├── errors/
│   ├── pagination/
│   └── permissions/
├── modules/
│   ├── identity/
│   ├── organizations/
│   ├── documents/
│   ├── ingestion/
│   ├── data_quality/
│   ├── alignment/
│   ├── knowledge/
│   ├── search/
│   ├── kpi/
│   ├── analysis/
│   ├── agents/
│   ├── recommendations/
│   ├── decisions/
│   └── audit/
├── integrations/
├── infrastructure/
└── tests/
```

Каждый модуль должен содержать:

```text
domain/
application/
infrastructure/
api/
tests/
```

Не требуется догматично реализовывать полный DDD. Важно сохранить понятные границы.

---

## 8. Структура frontend

```text
apps/web/src/
├── app/
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── documents/
│   ├── alignment/
│   ├── knowledge/
│   ├── kpi/
│   ├── analysis/
│   ├── decisions/
│   ├── data-quality/
│   ├── sources/
│   └── admin/
├── entities/
├── shared/
│   ├── api/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── types/
└── widgets/
```

---

## 9. Правила разработки в Cursor

### 9.1. Один запрос — одна задача

Не просить Cursor одновременно:

- изменить схему базы;
- сделать API;
- создать UI;
- написать тесты;
- исправить unrelated код.

Задачи должны быть узкими и проверяемыми.

### 9.2. Сначала спецификация, потом код

Перед созданием функции Cursor должен получить:

- цель;
- вход;
- выход;
- ограничения;
- acceptance criteria;
- затрагиваемые файлы;
- запрещенные изменения.

### 9.3. Не разрешать «магические» решения

Cursor не должен:

- создавать скрытые fallback;
- подставлять фиктивные данные;
- глушить исключения;
- делать автоматический `except Exception: pass`;
- обходить проверки Trust;
- создавать дублирующую модель.

### 9.4. Всегда обновлять тесты

Любое изменение бизнес-правила должно сопровождаться:

- unit test;
- integration test при необходимости;
- обновлением fixtures;
- проверкой миграции.

### 9.5. Сохранять архитектурные решения

Значимые решения оформляются как ADR:

```text
docs/decisions/ADR-0001-modular-monolith.md
```

---

## 10. Рекомендуемые Cursor Rules

В `.cursor/rules/` следует зафиксировать:

### `architecture.mdc`

- модульный монолит;
- запрет прямых зависимостей между инфраструктурой доменов;
- единый audit;
- единый permission layer;
- единый event envelope.

### `truth-first.mdc`

- нельзя генерировать бизнес-факты;
- нельзя подменять отсутствующие данные;
- анализ блокируется при критических пропусках;
- все выводы имеют источники.

### `database.mdc`

- все миграции через Alembic;
- старые значения не удаляются без политики;
- критические сущности версионируются;
- внешние ID не являются primary key.

### `api.mdc`

- Pydantic schemas;
- versioned endpoints;
- типизированные ошибки;
- permission check;
- audit;
- idempotency для write-операций.

### `frontend.mdc`

- состояния loading, empty, partial, stale, conflict, error;
- Trust всегда видим;
- факты и AI-выводы визуально различаются;
- критические действия требуют подтверждения.

### `testing.mdc`

- happy path;
- permission test;
- missing data test;
- conflict test;
- stale data test;
- audit test.

---

## 11. Среды разработки

Минимальный набор:

- local;
- development;
- staging;
- production.

### Local

Используется для разработки:

- PostgreSQL;
- MinIO;
- Redis;
- локальный mail catcher;
- mock connector;
- mock LLM provider.

### Staging

Должен быть максимально близок к production.

Production-данные нельзя переносить в staging без маскирования и разрешения.

---

## 12. Конфигурация

Конфигурация хранится через environment variables и централизованный config layer.

Минимальные группы:

- database;
- storage;
- redis;
- auth;
- encryption;
- LLM providers;
- rate limits;
- Trust thresholds;
- freshness rules;
- feature flags;
- observability.

Секреты не хранятся в git.

---

## 13. Первая итерация: Foundation

Цель:

> Создать безопасный каркас продукта.

Задачи:

- инициализировать monorepo;
- настроить backend;
- настроить frontend;
- поднять PostgreSQL;
- поднять MinIO;
- поднять Redis;
- создать auth;
- создать Company;
- создать User;
- создать Role;
- создать Department;
- создать AuditEvent;
- создать базовый layout;
- настроить CI;
- настроить миграции;
- настроить health checks.

Acceptance criteria:

- пользователь входит;
- видит пустой Dashboard;
- права работают;
- audit пишется;
- приложение запускается одной командой;
- CI проходит.

---

## 14. Вторая итерация: Document Foundation

Цель:

> Загрузить документ, сохранить оригинал и управлять версиями.

Задачи:

- Document;
- DocumentVersion;
- DocumentFile;
- upload API;
- object storage;
- checksum;
- duplicate detection;
- status pipeline;
- document list;
- document card;
- original viewer;
- version history.

Acceptance criteria:

- PDF, DOCX и XLSX загружаются;
- оригинал доступен;
- дубликат обнаруживается;
- версия не перезаписывается;
- история видна;
- доступ аудируется.

---

## 15. Третья итерация: Document Intelligence

Цель:

> Извлечь из документа структурированные утверждения.

Задачи:

- text extraction;
- page/section fragments;
- OCR только как fallback;
- classification;
- metadata extraction;
- statement extraction;
- structured output;
- source anchors;
- review UI;
- confirm/reject flow;
- extraction confidence.

Типы утверждений MVP:

- обязанность;
- ответственный;
- срок;
- KPI;
- лимит;
- этап процесса.

Acceptance criteria:

- пользователь видит фрагмент;
- подтверждает или отклоняет утверждение;
- утверждение содержит ссылку на источник;
- AI не создает подтвержденное знание автоматически.

---

## 16. Четвертая итерация: Data Ingestion

Цель:

> Получить фактические данные из одного реального источника.

Рекомендуемый первый источник:

- CRM;
- система задач;
- либо структурированный CSV/XLSX.

Выбирать источник следует по реальному сценарию первой компании.

Задачи:

- Source Registry;
- Connector;
- IngestionJob;
- RawPayload;
- file connector;
- один API connector;
- normalization;
- canonical records;
- sync status;
- retry;
- error handling;
- source dashboard.

Acceptance criteria:

- источник подключается;
- данные сохраняются в Raw Layer;
- повторная синхронизация не создает дубли;
- виден lineage;
- ошибки не скрываются.

---

## 17. Пятая итерация: Data Quality

Цель:

> Не допустить плохие данные в критический анализ.

Задачи:

- required field checks;
- type checks;
- date checks;
- duplicate checks;
- range checks;
- stale data rules;
- quarantine;
- issue ownership;
- Data Doctor dashboard;
- Trust Index источника.

Acceptance criteria:

- некорректная запись попадает в карантин;
- пользователь видит причину;
- критический анализ получает блокировку;
- исправление аудируется.

---

## 18. Шестая итерация: Entity Resolution

Цель:

> Связать записи разных источников с одним бизнес-объектом.

Для MVP достаточно:

- контрагентов;
- сотрудников;
- документов.

Задачи:

- exact matching;
- deterministic matching;
- candidate matching;
- manual confirmation;
- merge history;
- split operation;
- confidence;
- Trust recalculation.

Acceptance criteria:

- похожие записи создают кандидата;
- критическое объединение требует подтверждения;
- исходные записи сохраняются;
- merge можно проследить.

---

## 19. Седьмая итерация: Reality Alignment

Цель:

> Сравнить документ с реальной работой компании.

Первые проверки MVP:

- нормативный срок против фактического;
- назначенный ответственный против фактического исполнителя;
- нормативный KPI против фактически используемого;
- описанный этап против событий процесса.

Задачи:

- AlignmentCheck;
- AlignmentIssue;
- comparison rules;
- evidence;
- severity;
- owner workflow;
- confirm/reject;
- accepted deviation;
- Alignment Score;
- proposed document change.

Acceptance criteria:

- система показывает «как должно быть»;
- показывает «как есть»;
- показывает доказательства;
- владелец подтверждает или отклоняет;
- AI не меняет документ автоматически.

---

## 20. Восьмая итерация: Knowledge Base

Цель:

> Создать проверенную корпоративную базу знаний.

Задачи:

- KnowledgeRecord;
- BusinessObject;
- KnowledgeRelation;
- statuses;
- versions;
- valid time;
- system time;
- Trust;
- source;
- lineage;
- ownership;
- conflicts;
- full-text search;
- semantic search;
- basic graph.

Acceptance criteria:

- знание имеет источник;
- спорное знание маркировано;
- старая версия доступна;
- пользователь может пройти от знания к оригиналу;
- права соблюдаются.

---

## 21. Девятая итерация: KPI Foundation

Цель:

> Создать минимальный расчетный слой для управленческого анализа.

Задачи:

- KPI definition;
- formula;
- source mapping;
- target;
- actual;
- period;
- owner;
- Trust;
- version;
- history;
- recalculation.

Acceptance criteria:

- KPI воспроизводим;
- формула видна;
- источники видны;
- при конфликте данных показатель маркируется;
- изменение формулы создает версию.

---

## 22. Десятая итерация: LLM Gateway

Цель:

> Создать единый безопасный доступ к AI-моделям.

Задачи:

- provider abstraction;
- model registry;
- prompt registry;
- structured output;
- token and cost logging;
- retry;
- timeout;
- rate limits;
- redaction;
- audit;
- prompt injection guards;
- feature flags.

Acceptance criteria:

- ни один модуль не вызывает модель напрямую;
- запрос и ответ аудируются;
- structured output валидируется;
- секретные поля не передаются без прав;
- невалидный ответ отклоняется.

---

## 23. Одиннадцатая итерация: Context Builder

Цель:

> Формировать минимально необходимый и разрешенный контекст.

Задачи:

- question parsing;
- scope;
- period;
- minimum data set;
- permissions;
- Trust filter;
- freshness filter;
- conflict detection;
- source selection;
- context snapshot.

Acceptance criteria:

- закрытые данные не попадают в контекст;
- устаревшие данные маркируются;
- при критическом пропуске анализ блокируется;
- snapshot сохраняется.

---

## 24. Двенадцатая итерация: AI Agents

Состав MVP:

- Executive AI;
- один профильный агент;
- Data Doctor;
- Critic AI.

Рекомендуемый профильный агент выбирается по первому реальному сценарию:

- Sales AI;
- Finance AI;
- Operations AI.

Задачи:

- AgentProfile;
- Decision DNA;
- independent runs;
- structured opinions;
- evidence;
- missing data;
- disagreement;
- critic pass;
- synthesis.

Acceptance criteria:

- агенты анализируют независимо;
- выводы не смешиваются до debate;
- источники видны;
- разногласия сохраняются;
- при нехватке данных ответ блокируется.

---

## 25. Тринадцатая итерация: Executive Dashboard

Цель:

> Дать руководителю рабочий интерфейс принятия решения.

Задачи:

- readiness block;
- Completeness;
- Trust;
- Alignment;
- document health;
- question form;
- analysis status;
- agent opinions;
- evidence viewer;
- recommendation card;
- decision form.

Acceptance criteria:

- руководитель задает вопрос;
- видит качество данных;
- видит доказательства;
- видит ограничения;
- может принять или отклонить рекомендацию.

---

## 26. Четырнадцатая итерация: Decision Memory

Цель:

> Связать анализ с реальным управленческим результатом.

Задачи:

- Decision;
- selected option;
- rationale;
- tasks;
- checkpoints;
- expected result;
- actual result;
- result review;
- lessons;
- audit.

Acceptance criteria:

- решение сохраняется;
- назначается ответственный;
- задается контрольная дата;
- фиксируется фактический результат;
- видна разница между прогнозом и фактом.

---

## 27. Рекомендуемый первый сквозной кейс

Для MVP необходимо выбрать один кейс.

Хороший пример:

> Проверка соответствия регламента обработки лидов фактической работе отдела продаж.

Нужные данные:

- регламент продаж;
- должностные инструкции;
- KPI отдела;
- CRM-события;
- время создания лида;
- время первого контакта;
- ответственный;
- статус;
- причина отказа.

Система должна:

1. загрузить документы;
2. извлечь сроки, обязанности и KPI;
3. получить CRM-данные;
4. сравнить нормативные и фактические сроки;
5. выявить отклонения;
6. получить подтверждение владельца;
7. сформировать знания;
8. ответить руководителю, почему не выполняется план;
9. показать источники;
10. сохранить решение.

---

## 28. Definition of Ready

Задача готова к разработке, если известны:

- бизнес-цель;
- пользователь;
- вход;
- выход;
- правила;
- ошибки;
- права;
- аудит;
- acceptance criteria;
- затрагиваемые сущности;
- влияние на существующие спецификации.

---

## 29. Definition of Done

Задача завершена, если:

- код реализован;
- миграции созданы;
- API документировано;
- UI поддерживает состояния;
- права проверены;
- audit работает;
- тесты проходят;
- ошибки понятны;
- нет фиктивных данных;
- документация обновлена;
- acceptance criteria подтверждены.

---

## 30. Стратегия тестирования

### Unit Tests

Для:

- Trust calculations;
- Alignment rules;
- KPI formulas;
- permission rules;
- state transitions;
- validation.

### Integration Tests

Для:

- database;
- storage;
- connectors;
- LLM Gateway;
- search;
- queues.

### Contract Tests

Для внешних API.

### End-to-End Tests

Для полного пути пользователя.

### Security Tests

Для:

- permissions;
- prompt injection;
- data leakage;
- insecure direct object reference;
- export;
- audit.

---

## 31. Обязательные негативные тесты

Нужно проверить:

- отсутствует источник;
- источник устарел;
- документ конфликтует с другой версией;
- Trust ниже порога;
- пользователь не имеет доступа;
- AI возвращает невалидный JSON;
- коннектор повторяет событие;
- Entity Resolution ошибочен;
- формула KPI повреждена;
- критическое действие не подтверждено;
- документ содержит prompt injection.

---

## 32. Тестовые данные

Fixtures должны включать:

- действующий регламент;
- устаревшую версию;
- конфликтующий документ;
- CRM-события;
- пропущенные поля;
- дубли контрагентов;
- устаревший источник;
- низкий Trust;
- решение руководителя;
- фактический результат.

Тестовые данные должны быть синтетическими.

---

## 33. CI/CD

Минимальный pipeline:

```text
Lint
  ↓
Type Check
  ↓
Unit Tests
  ↓
Migration Check
  ↓
Integration Tests
  ↓
Security Scan
  ↓
Build
  ↓
Deploy to Staging
  ↓
Smoke Tests
```

Production deploy выполняется только после staging-проверки.

---

## 34. Code Review Checklist

Проверить:

- соответствует ли функция исходному ТЗ;
- не добавляет ли лишнюю платформенность;
- есть ли источник у фактов;
- учитывается ли Trust;
- сохраняется ли история;
- проверяются ли права;
- создается ли audit;
- есть ли negative path;
- нет ли скрытого fallback;
- обновлена ли документация.

---

## 35. Database Migration Checklist

Перед merge:

- миграция обратима;
- нет потери данных;
- есть default или backfill;
- индекс обоснован;
- внешние ключи корректны;
- история сохраняется;
- staging migration протестирована.

---

## 36. API Checklist

Каждый endpoint должен иметь:

- route;
- method;
- request schema;
- response schema;
- error schema;
- permission;
- audit behavior;
- idempotency requirement;
- pagination;
- OpenAPI description;
- tests.

---

## 37. AI Prompt Checklist

Каждый AI-сценарий должен иметь:

- роль;
- цель;
- разрешенный контекст;
- запрещенные действия;
- required output schema;
- rule for missing data;
- citation rule;
- Trust threshold;
- prompt injection handling;
- version;
- evaluation set.

---

## 38. Evaluation AI

Нельзя оценивать AI только субъективно.

Нужен набор проверок:

- источник существует;
- цитата соответствует фрагменту;
- факт не выдуман;
- конфликт не скрыт;
- ограничение указано;
- missing data выявлены;
- рекомендация отделена от факта;
- output соответствует схеме.

---

## 39. Feature Flags

Через feature flags включаются:

- новые агенты;
- новые коннекторы;
- новые extraction models;
- proactive analysis;
- simulation;
- write-back.

Новая функция не должна сразу становиться обязательной для production.

---

## 40. Логирование и приватность

Запрещено логировать:

- пароли;
- токены;
- секреты;
- полные закрытые документы;
- персональные данные без необходимости;
- полный prompt при наличии чувствительных данных.

Нужно логировать:

- trace ID;
- тип операции;
- статус;
- время;
- модель;
- стоимость;
- ошибки;
- ссылки на защищенные ресурсы.

---

## 41. Backup и восстановление

До production необходимо:

- настроить backup PostgreSQL;
- настроить backup object storage;
- проверить restore;
- задокументировать RPO;
- задокументировать RTO;
- создать runbook восстановления.

---

## 42. Security Baseline

Обязательно:

- HTTPS;
- MFA для критических ролей;
- шифрование at rest;
- vault для секретов;
- RBAC + object access;
- audit;
- rate limits;
- dependency scanning;
- SAST;
- backup;
- session expiry;
- upload validation;
- antivirus scanning при необходимости.

---

## 43. Порядок развертывания у первой компании

1. Подготовить инфраструктуру.
2. Настроить пользователей и роли.
3. Определить владельцев документов.
4. Загрузить ограниченный набор документов.
5. Подключить один фактический источник.
6. Провести первичную проверку качества.
7. Настроить правила Alignment.
8. Подтвердить знания.
9. Настроить один AI-кейс.
10. Обучить руководителя и владельцев процессов.
11. Запустить пилот.
12. Зафиксировать ошибки и результаты.

---

## 44. Пилот

Рекомендуемая граница пилота:

- один отдел;
- один процесс;
- один реальный вопрос руководителя;
- 20–100 документов;
- один внешний источник;
- 3–10 пользователей;
- один профильный AI-агент.

Пилот не должен охватывать всю компанию сразу.

---

## 45. Метрики успеха пилота

- доля обработанных документов;
- доля подтвержденных утверждений;
- доля документов с владельцем;
- количество найденных расхождений;
- время разрешения расхождения;
- доля ответов с доказательствами;
- количество блокировок из-за плохих данных;
- полезность рекомендаций;
- время от вопроса до решения;
- фактический эффект решения.

---

## 46. Критерии готовности к расширению

Расширять систему можно, если:

- один сквозной сценарий стабилен;
- источники надежны;
- права проверены;
- audit полный;
- Trust объясним;
- пользователи подтверждают ценность;
- Decision Memory используется;
- нет критических архитектурных долгов.

---

## 47. Что не следует делать до завершения MVP

Не следует:

- подключать десять CRM;
- строить marketplace;
- делать мобильное приложение полностью;
- создавать 20 агентов;
- строить универсальную process mining платформу;
- автоматизировать платежи;
- реализовывать self-optimization;
- создавать собственную модель;
- проектировать multi-tenancy;
- переписывать систему в микросервисы;
- строить сложный Knowledge Graph UI без реального кейса.

---

## 48. Реестр архитектурных рисков

### Риск 1. Документы не соответствуют реальности

Мера:

- Reality Alignment до AI-анализа.

### Риск 2. Низкое качество источников

Мера:

- Data Quality, quarantine, Trust.

### Риск 3. AI выдумывает

Мера:

- structured context, citations, blocking, evaluations.

### Риск 4. Слишком широкий MVP

Мера:

- один отдел, один процесс, один источник.

### Риск 5. Сложная архитектура раньше времени

Мера:

- modular monolith.

### Риск 6. Пользователь не доверяет выводам

Мера:

- evidence chain и Explain Everything.

### Риск 7. Конфиденциальность

Мера:

- role-based access, data minimization, audit.

---

## 49. Технический долг

Каждый debt item должен содержать:

- описание;
- причину;
- риск;
- затронутые модули;
- приоритет;
- владелец;
- срок пересмотра.

Технический долг не должен скрываться в комментариях кода.

---

## 50. Документация кода

Минимум:

- README;
- setup;
- architecture overview;
- environment variables;
- migration guide;
- connector guide;
- prompt guide;
- deployment runbook;
- backup runbook;
- incident runbook;
- API docs.

---

## 51. Команды разработки

Рекомендуется добавить Makefile:

```text
make setup
make dev
make test
make lint
make typecheck
make migrate
make seed
make e2e
make build
make up
make down
```

---

## 52. Seed Data

Seed должен создавать:

- одну компанию;
- администратора;
- руководителя;
- отдел;
- должности;
- тестовые документы;
- источник;
- KPI;
- тестовое расхождение;
- анализ;
- решение.

---

## 53. Локальный demo-сценарий

После `make demo` пользователь должен получить:

1. тестовую компанию;
2. регламент продаж;
3. CRM-выгрузку;
4. найденное расхождение;
5. подтвержденное знание;
6. вопрос руководителя;
7. выводы агентов;
8. рекомендацию;
9. решение;
10. контрольный результат.

---

## 54. Итоговый acceptance test продукта

Система проходит тест, если:

1. пользователь загружает регламент;
2. система сохраняет оригинал;
3. извлекает срок и обязанность;
4. пользователь подтверждает утверждение;
5. система получает фактические данные;
6. обнаруживает отклонение;
7. показывает доказательства;
8. владелец подтверждает расхождение;
9. Knowledge Base обновляется;
10. руководитель задает вопрос;
11. Data Doctor проверяет данные;
12. агенты анализируют независимо;
13. Critic AI формирует возражения;
14. Executive AI создает сводку;
15. все выводы имеют источники;
16. руководитель принимает решение;
17. создается контрольная точка;
18. система сохраняет фактический результат.

---

## 55. Финальный состав MVP

MVP должен включать:

### Foundation

- компания;
- пользователи;
- роли;
- подразделения;
- права;
- аудит.

### Documents

- загрузка;
- версии;
- extraction;
- statements;
- source anchors;
- confirmation.

### Data

- source registry;
- file import;
- один API connector;
- Raw Layer;
- normalization;
- Data Quality;
- Entity Resolution.

### Reality

- comparison rules;
- Alignment Issues;
- confirmation workflow;
- proposed changes.

### Knowledge

- records;
- relations;
- Trust;
- lineage;
- search.

### AI

- LLM Gateway;
- Context Builder;
- Executive AI;
- профильный агент;
- Data Doctor;
- Critic AI;
- evidence-based synthesis.

### Executive

- Dashboard;
- question flow;
- recommendation;
- decision;
- Decision Memory;
- result control.

---

## 56. После MVP

После доказательства основного сценария можно последовательно добавлять:

- второй фактический источник;
- второй отдел;
- дополнительные типы документов;
- новые Alignment Rules;
- дополнительные KPI;
- новые профильные агенты;
- сценарный анализ;
- Process Intelligence;
- проактивные уведомления;
- расширенную мобильную версию;
- controlled write-back.

---

## 57. Контроль исходной идеи

Перед каждой новой функцией нужно ответить:

1. Помогает ли она привести документацию к реальному состоянию?
2. Улучшает ли качество корпоративных знаний?
3. Повышает ли доказательность анализа?
4. Помогает ли руководителю принять решение?
5. Нужна ли она для текущего MVP?

Если на первые четыре вопроса ответ «нет», функция не относится к ядру проекта.

Если на пятый ответ «нет», функция переносится в backlog.

---

## 58. Главный принцип реализации

> Не строить сразу универсальную операционную систему компании. Сначала доказать, что Business OS умеет превратить документы и реальные данные одного процесса в надежную управленческую рекомендацию.
