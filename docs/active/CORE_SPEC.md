# CORE_SPEC.md

# Business OS — Спецификация технического ядра

**Версия:** 1.0  
**Статус:** базовая спецификация  
**Назначение:** определить техническое ядро Business OS, границы подсистем, основные сущности, потоки данных, правила взаимодействия и состав MVP.

---

## 1. Цель

Core Business OS должен обеспечить единый технический фундамент для:

- загрузки и хранения документации;
- получения фактических данных из рабочих систем;
- проверки качества;
- сверки документов с реальной деятельностью;
- формирования корпоративной базы знаний;
- запуска доказательного AI-анализа;
- выдачи рекомендаций руководителю;
- сохранения решений и контроля результата.

Главный результат ядра:

> Надежная, прослеживаемая и управляемая система, в которой каждый вывод можно проверить до первоисточника.

---

## 2. Граница продукта

Business OS в первой версии создается:

- для одной компании;
- как закрытая внутренняя система;
- без публичного SaaS;
- без мультиарендности;
- без маркетплейса;
- без автономных критических действий;
- без собственной foundation model;
- без попытки заменить все существующие системы.

Business OS не должна становиться новой CRM, ERP или бухгалтерией.

Она должна:

- подключаться к существующим системам;
- получать из них данные;
- связывать данные с документацией;
- выявлять расхождения;
- формировать проверенную модель компании;
- поддерживать анализ и принятие решений.

---

## 3. Главный пользовательский поток

```text
Компания подключает документы и источники
                ↓
Система загружает и сохраняет оригиналы
                ↓
Извлекает текст, структуру и утверждения
                ↓
Получает фактические данные из CRM/ERP/банка/задач
                ↓
Проверяет качество, свежесть и происхождение
                ↓
Сравнивает «как должно быть» и «как есть»
                ↓
Владелец подтверждает или отклоняет расхождения
                ↓
Формируется корпоративная база знаний
                ↓
Руководитель задает вопрос
                ↓
AI-агенты анализируют подтвержденные знания
                ↓
Система показывает выводы, источники и ограничения
                ↓
Руководитель принимает решение
                ↓
Решение сохраняется и контролируется
```

---

## 4. Архитектурные принципы

### 4.1. Truth First

Ни одна критическая рекомендация не формируется при недостатке данных.

### 4.2. Source First

Любой факт, показатель или вывод должен иметь источник.

### 4.3. History First

Изменения не перезаписывают прошлое без следа.

### 4.4. Human in Control

Человек утверждает:

- изменения документов;
- критические знания;
- управленческие решения;
- изменения KPI;
- изменения полномочий;
- внешние действия.

### 4.5. Read-Only by Default

Интеграции MVP преимущественно читают данные.

### 4.6. Separation of States

Система различает:

- нормативное;
- фактическое;
- предлагаемое;
- подтвержденное;
- спорное;
- архивное.

### 4.7. Explainability by Design

Объяснимость является частью модели данных, а не дополнением интерфейса.

---

## 5. Основные подсистемы

### 5.1. Identity and Access

Отвечает за:

- пользователей;
- роли;
- должности;
- подразделения;
- права;
- сессии;
- доступ AI-агентов;
- аудит доступа.

### 5.2. Document Intelligence

Отвечает за:

- загрузку документов;
- хранение оригиналов;
- извлечение текста;
- классификацию;
- версии;
- метаданные;
- извлечение утверждений;
- ссылки на фрагменты;
- AI-резюме;
- конфликты документов.

### 5.3. Data Ingestion

Отвечает за:

- источники;
- коннекторы;
- синхронизацию;
- Raw Layer;
- нормализацию;
- дедупликацию;
- Entity Resolution;
- Data Quality;
- Lineage;
- карантин;
- фактические события.

### 5.4. Reality Alignment

Отвечает за:

- сравнение нормативных утверждений с фактическими данными;
- выявление расхождений;
- Alignment Score;
- workflow подтверждения;
- предложения изменений;
- допустимые отклонения;
- аудит разрешения конфликтов.

### 5.5. Knowledge Base

Отвечает за:

- подтвержденные знания;
- объекты;
- связи;
- версии;
- временную модель;
- Trust Index;
- Source of Truth;
- поиск;
- граф связей;
- права доступа;
- контекст для аналитики.

### 5.6. AI Analysis

Отвечает за:

- Context Builder;
- проверку минимального набора данных;
- независимый анализ агентов;
- Data Doctor;
- Critic AI;
- debate;
- Executive Synthesis;
- рекомендации;
- сценарии;
- ограничения;
- Decision Memory.

### 5.7. Executive Workspace

Отвечает за:

- состояние данных;
- состояние документации;
- вопросы руководителя;
- выводы агентов;
- источники;
- рекомендации;
- решения;
- контроль результата.

### 5.8. Audit and Observability

Отвечает за:

- аудит действий;
- логи;
- метрики;
- трассировку;
- мониторинг источников;
- версии правил;
- воспроизводимость выводов.

---

## 6. Логические слои

```text
Presentation Layer
    Executive Dashboard
    Document Workspace
    Data Quality Workspace
    Admin Workspace

Application Layer
    Document Services
    Alignment Services
    Knowledge Services
    Analysis Services
    Decision Services

Domain Layer
    Documents
    Knowledge
    Processes
    KPI
    Sources
    Decisions
    Users
    Permissions

Infrastructure Layer
    Database
    Object Storage
    Search
    Vector Index
    Queue
    LLM Gateway
    Connector Runtime
    Monitoring
```

---

## 7. Основные доменные сущности

Минимальный набор:

- Company;
- User;
- Role;
- Position;
- Department;
- Permission;
- Source;
- Connector;
- IngestionJob;
- RawPayload;
- Document;
- DocumentVersion;
- DocumentFragment;
- ExtractedStatement;
- Fact;
- KnowledgeRecord;
- KnowledgeRelation;
- BusinessObject;
- Event;
- DataQualityIssue;
- Conflict;
- AlignmentCheck;
- AlignmentIssue;
- Process;
- ProcessStep;
- KPI;
- AIAnalysis;
- AgentOpinion;
- Recommendation;
- Decision;
- DecisionTask;
- ReviewCheckpoint;
- AuditEvent.

---

## 8. Универсальные поля сущностей

Каждая критическая сущность должна иметь:

- id;
- company_id;
- status;
- created_at;
- updated_at;
- created_by;
- owner_id;
- source_id;
- version;
- trust_index;
- confidentiality;
- valid_from;
- valid_to;
- metadata;
- permissions;
- audit_reference.

Не все поля обязательны для каждой сущности, но модель должна поддерживать их единообразно.

---

## 9. Идентификаторы

Используются внутренние неизменяемые ID.

Внешние ID хранятся отдельно:

```text
internal_id
source_id
external_id
external_version
```

Нельзя использовать внешний ID как единственный идентификатор системы.

---

## 10. Документная модель

### Document

Представляет логический документ.

### DocumentVersion

Представляет конкретную редакцию.

### DocumentFile

Представляет физический файл.

### DocumentFragment

Представляет страницу, раздел, абзац, таблицу или ячейку.

### ExtractedStatement

Представляет извлеченное утверждение:

- обязанность;
- срок;
- KPI;
- условие;
- лимит;
- ответственного;
- этап процесса;
- право;
- запрет.

---

## 11. Модель фактов

Fact должен содержать:

- subject;
- predicate;
- value;
- unit;
- period;
- source;
- observed_at;
- valid_from;
- valid_to;
- trust_index;
- status;
- lineage;
- scope.

Факт не должен храниться без источника.

---

## 12. Модель знаний

KnowledgeRecord создается из:

- подтвержденного нормативного утверждения;
- подтвержденного фактического наблюдения;
- утвержденного решения;
- воспроизводимого расчета;
- принятого отклонения.

KnowledgeRecord не создается напрямую из текста ответа AI.

---

## 13. Модель состояния

Система хранит:

- текущее состояние;
- историю изменений;
- временные интервалы;
- события перехода.

Для критических сущностей нельзя ограничиваться только текущим значением.

---

## 14. Модель доверия

Trust Index должен быть вычисляемым и объяснимым.

Пример факторов:

- надежность источника;
- свежесть;
- полнота;
- отсутствие конфликтов;
- качество распознавания;
- подтверждение владельцем;
- качество Entity Resolution;
- доля ручного ввода;
- стабильность данных.

Для каждого индекса сохраняются:

- итоговый балл;
- факторы;
- веса;
- версия формулы;
- дата расчета;
- причины снижения.

---

## 15. Модель соответствия реальности

AlignmentCheck связывает:

- нормативное утверждение;
- фактический показатель;
- метод сравнения;
- допустимое отклонение;
- результат;
- влияние;
- Trust Index;
- владельца;
- статус.

---

## 16. Модель конфликта

Conflict содержит:

- тип;
- объекты;
- значения;
- источники;
- приоритеты;
- влияние;
- статус;
- владельца;
- решение;
- историю;
- затронутые выводы.

Конфликт не должен удаляться после разрешения.

---

## 17. Модель AI-анализа

AIAnalysis содержит:

- вопрос;
- инициатора;
- scope;
- период;
- minimum data set;
- snapshot знаний;
- агентов;
- статусы;
- выводы;
- источники;
- ограничения;
- итог;
- решение;
- контрольные даты.

---

## 18. Модель агента

AgentProfile содержит:

- role;
- domain;
- Decision DNA;
- доступные знания;
- запрещенные поля;
- minimum trust;
- required evidence;
- escalation rules;
- enabled tools;
- version.

---

## 19. Модель рекомендации

Recommendation содержит:

- evidence;
- assumptions;
- action;
- alternatives;
- expected_effect;
- risks;
- cost;
- timeframe;
- trust_index;
- confidence;
- status;
- human_decision.

---

## 20. Модель решения

Decision содержит:

- question;
- context;
- selected_option;
- rejected_options;
- rationale;
- owner;
- approver;
- tasks;
- checkpoints;
- expected_result;
- actual_result;
- lesson.

---

## 21. Событийная модель

События используются для:

- синхронизации;
- истории;
- перерасчетов;
- уведомлений;
- аудита;
- повторной обработки.

Минимальные события:

- SourceConnected;
- SyncStarted;
- SyncCompleted;
- SyncFailed;
- DocumentUploaded;
- DocumentProcessed;
- StatementExtracted;
- FactConfirmed;
- ConflictDetected;
- AlignmentIssueDetected;
- AlignmentIssueResolved;
- KnowledgeUpdated;
- AnalysisRequested;
- AnalysisBlocked;
- RecommendationCreated;
- DecisionMade;
- ReviewDue;
- ResultRecorded.

---

## 22. Event Envelope

Каждое событие содержит:

- event_id;
- event_type;
- company_id;
- occurred_at;
- received_at;
- actor_id;
- source_id;
- object_type;
- object_id;
- payload;
- trace_id;
- version;
- trust_index;
- processing_status.

---

## 23. Поток документа

```text
Upload
  ↓
Store Original
  ↓
Create Document and Version
  ↓
Extract
  ↓
Classify
  ↓
Create Fragments
  ↓
Extract Statements
  ↓
Validate
  ↓
Review
  ↓
Create Knowledge Candidates
  ↓
Confirm
  ↓
Publish Knowledge
```

---

## 24. Поток фактических данных

```text
Connector
  ↓
Raw Payload
  ↓
Schema Validation
  ↓
Normalization
  ↓
Entity Resolution
  ↓
Quality Checks
  ↓
Canonical Object/Event
  ↓
Fact
  ↓
Reality Alignment
  ↓
Knowledge Base
```

---

## 25. Поток управленческого вопроса

```text
Question
  ↓
Scope Detection
  ↓
Minimum Data Set
  ↓
Access Check
  ↓
Trust and Freshness Check
  ↓
Context Snapshot
  ↓
Independent Agent Analysis
  ↓
Critic Review
  ↓
Synthesis
  ↓
Recommendation
  ↓
Human Decision
  ↓
Decision Memory
```

---

## 26. Правила блокировки

Анализ блокируется, если:

- отсутствует обязательный источник;
- данные устарели;
- есть нерешенный критический конфликт;
- Trust Index ниже порога;
- нет доступа;
- не подтвержден Entity Resolution;
- нормативное утверждение спорное;
- фактический период неполный;
- нарушена целостность формулы KPI.

---

## 27. Правила перерасчета

Изменение источника должно запускать только зависимые перерасчеты.

Пример:

```text
Изменился документ
        ↓
Изменились утверждения
        ↓
Пересчитался Alignment
        ↓
Обновились связанные знания
        ↓
Устарели зависимые рекомендации
```

---

## 28. Кэширование

Допускается кэширование:

- сводных KPI;
- результатов поиска;
- готовых контекстов;
- аналитических агрегатов;
- UI-сводок.

Кэш не является источником истины и должен иметь:

- TTL;
- версию;
- зависимости;
- механизм инвалидирования.

---

## 29. Хранилища

### Реляционная база

Для:

- пользователей;
- документов;
- версий;
- фактов;
- знаний;
- решений;
- прав;
- статусов;
- аудита.

### Object Storage

Для:

- оригиналов;
- вложений;
- сканов;
- экспортов;
- больших сырых пакетов.

### Search Index

Для:

- полнотекстового поиска;
- фильтрации;
- подсветки фрагментов.

### Vector Index

Для:

- семантического поиска;
- retrieval.

### Queue

Для:

- обработки документов;
- синхронизации;
- повторных попыток;
- AI-задач;
- перерасчетов.

---

## 30. Рекомендуемый технологический стек MVP

Пример практичного стека:

- Frontend: Next.js / TypeScript;
- Backend API: Python FastAPI;
- Database: PostgreSQL;
- Object Storage: S3-compatible storage;
- Search: PostgreSQL Full Text или OpenSearch;
- Vector Search: pgvector;
- Queue: Redis + worker framework;
- Authentication: Keycloak, Auth0 или корпоративный SSO;
- LLM Gateway: отдельный сервис;
- Observability: OpenTelemetry + Prometheus/Grafana;
- Deployment: Docker Compose на старте, затем Kubernetes при необходимости.

Выбор стека может быть изменен без изменения доменной модели.

---

## 31. LLM Gateway

Все обращения к моделям проходят через единый шлюз.

Он отвечает за:

- выбор модели;
- права;
- rate limits;
- логирование;
- маскирование;
- версии prompts;
- защиту от prompt injection;
- structured output;
- retry;
- стоимость;
- аудит.

Подсистемы не должны вызывать внешние модели напрямую.

---

## 32. Structured Output

AI-операции должны возвращать структурированный результат.

Пример:

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

Свободный текст является представлением, а не основной формой хранения.

---

## 33. API-принципы

API должно быть:

- версионируемым;
- типизированным;
- идемпотентным;
- аудируемым;
- защищенным;
- согласованным с правами;
- пригодным для повторной обработки.

---

## 34. Основные API-группы

- `/auth`;
- `/users`;
- `/roles`;
- `/documents`;
- `/document-versions`;
- `/sources`;
- `/connectors`;
- `/ingestion`;
- `/data-quality`;
- `/facts`;
- `/knowledge`;
- `/relations`;
- `/alignment`;
- `/processes`;
- `/kpis`;
- `/analyses`;
- `/agents`;
- `/recommendations`;
- `/decisions`;
- `/audit`;
- `/search`.

---

## 35. Права доступа

Минимальная модель:

- RBAC по ролям;
- ABAC по объектам и атрибутам;
- права по подразделению;
- права по проекту;
- уровень конфиденциальности;
- отдельные права AI.

Доступ проверяется:

- при поиске;
- при retrieval;
- при открытии источника;
- при экспорте;
- при AI-анализе.

---

## 36. Безопасность

Обязательные меры:

- шифрование в transit и at rest;
- секреты в vault;
- минимальные права;
- MFA для критических ролей;
- SSO при наличии;
- аудит доступа;
- маскирование;
- резервное копирование;
- восстановление;
- изоляция окружений;
- сканирование зависимостей;
- запрет секретов в prompts и logs.

---

## 37. Prompt Injection Protection

Система должна:

- считать документы данными, а не инструкциями;
- отделять system instructions;
- очищать подозрительные фрагменты;
- ограничивать инструменты;
- использовать allowlist операций;
- проверять structured output;
- логировать срабатывания;
- блокировать попытки изменить системные правила.

---

## 38. Аудит

AuditEvent должен фиксировать:

- actor;
- action;
- object;
- timestamp;
- before;
- after;
- source;
- IP/device при необходимости;
- trace_id;
- reason;
- result.

---

## 39. Наблюдаемость

Минимально:

- health checks;
- structured logs;
- metrics;
- tracing;
- job status;
- connector status;
- queue depth;
- document processing time;
- AI latency;
- AI cost;
- error rate;
- blocked analysis count.

---

## 40. Резервное копирование

Нужно обеспечить:

- backup базы;
- backup object storage;
- проверку восстановления;
- retention policy;
- журнал backup;
- разделение production и backup credentials.

---

## 41. Производительность MVP

Целевые ориентиры:

- открытие карточки — до 2 секунд;
- поиск — до 3 секунд;
- загрузка документа — подтверждение до 2 секунд;
- асинхронная обработка — с видимым статусом;
- дашборд — до 3 секунд при готовых агрегатах;
- AI-анализ — с отображением этапов, без блокировки UI.

---

## 42. Масштаб MVP

Ориентир первой версии:

- одна компания;
- до 500 пользователей;
- до 100 000 документов;
- до 10 миллионов фактических событий;
- 1–2 реальных коннектора;
- 2–4 AI-агента;
- один production-контур.

Это не жесткие лимиты, а проектная граница MVP.

---

## 43. Отказоустойчивость

При отказе AI:

- документы остаются доступны;
- поиск работает;
- данные не теряются;
- дашборды показывают последний проверенный срез;
- анализ получает статус unavailable.

При отказе источника:

- данные помечаются stale;
- Trust снижается;
- критические выводы блокируются.

---

## 44. Миграции

Все изменения схемы должны:

- быть версионируемыми;
- иметь rollback;
- тестироваться;
- сохранять историю;
- не удалять критические поля без миграционного плана.

---

## 45. Конфигурация

В конфигурации должны храниться:

- пороги Trust;
- правила свежести;
- источники истины;
- допустимые отклонения;
- роли;
- права;
- формулы KPI;
- список агентов;
- Decision DNA;
- Company Constitution.

Критические изменения конфигурации аудируются и подтверждаются.

---

## 46. Среды

Минимально:

- local;
- development;
- staging;
- production.

Данные production не должны бесконтрольно копироваться в development.

---

## 47. Тестирование

Нужны:

- unit tests;
- integration tests;
- contract tests коннекторов;
- migration tests;
- permission tests;
- lineage tests;
- AI structured output tests;
- hallucination guard tests;
- prompt injection tests;
- end-to-end сценарии.

---

## 48. Ключевые end-to-end сценарии

### Сценарий 1. Документ

- загрузить регламент;
- извлечь утверждения;
- подтвердить;
- опубликовать знания;
- открыть источник.

### Сценарий 2. Реальность

- получить данные из CRM;
- сравнить срок;
- выявить расхождение;
- подтвердить владельцем;
- создать новую версию документа.

### Сценарий 3. Анализ

- задать вопрос;
- проверить данные;
- получить независимые мнения;
- открыть доказательства;
- принять решение;
- поставить контроль.

---

## 49. Состав MVP

Обязательный MVP:

1. пользователи, роли и подразделения;
2. документы и версии;
3. PDF, DOCX, XLSX;
4. извлечение текста и утверждений;
5. ручное подтверждение;
6. файловый импорт;
7. один API-коннектор;
8. Raw Layer;
9. нормализация;
10. Data Quality;
11. Entity Resolution для контрагентов;
12. Reality Alignment для сроков и ответственности;
13. Knowledge Base;
14. поиск;
15. Trust Index;
16. Executive AI;
17. один профильный AI;
18. Data Doctor;
19. Critic AI;
20. ответы с источниками;
21. остановка при недостатке данных;
22. Executive Dashboard;
23. Decision Memory;
24. аудит.

---

## 50. Что исключено из MVP

- мультиарендность;
- публичный SaaS;
- marketplace;
- десятки коннекторов;
- автономные платежи;
- автономные кадровые действия;
- автоматическое утверждение документов;
- полная ERP;
- полная CRM;
- сложный process mining;
- массовая сценарная симуляция;
- self-optimizing company;
- собственная foundation model;
- универсальная отраслевая платформа.

---

## 51. Этапы реализации

### Этап 1. Foundation

- репозиторий;
- auth;
- roles;
- database;
- object storage;
- audit;
- base UI.

### Этап 2. Documents

- загрузка;
- версии;
- extraction;
- fragments;
- statements;
- review.

### Этап 3. Data

- source registry;
- file ingestion;
- API connector;
- Raw Layer;
- normalization;
- quality.

### Этап 4. Reality Alignment

- checks;
- issues;
- evidence;
- confirmation workflow;
- document update proposal.

### Этап 5. Knowledge

- records;
- relations;
- search;
- Trust;
- lineage.

### Этап 6. AI

- LLM Gateway;
- Context Builder;
- Executive AI;
- profile agent;
- Data Doctor;
- Critic;
- synthesis.

### Этап 7. Executive

- dashboard;
- question flow;
- recommendation;
- decision;
- monitoring.

---

## 52. Критерии готовности ядра

Ядро считается готовым, если система может пройти полный путь:

```text
Документ + фактический источник
            ↓
Проверенные утверждения и факты
            ↓
Выявленное расхождение
            ↓
Подтверждение владельца
            ↓
Обновленная база знаний
            ↓
Вопрос руководителя
            ↓
Доказательная рекомендация
            ↓
Решение и контроль
```

---

## 53. Главный принцип

> Техническое ядро Business OS должно обеспечивать не максимальное количество функций, а максимальную достоверность пути от документа и факта до управленческого решения.
