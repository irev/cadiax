# Target Architecture V2

Dokumen ini mendeskripsikan arsitektur target setelah fondasi phase akhir selesai. Fokusnya bukan mengganti semua komponen saat ini, tetapi memisahkan boundary yang masih bercampur dan menyiapkan sistem agar benar-benar berkembang menjadi `Autonomous Personal AI Assistant`.

Dokumen ini adalah turunan arsitektural dari `docs/specs/autonomous_ai_system_spec_extended.md`.

Semua boundary, service, dan modul target di dokumen ini termasuk scope target `v1.0.0`, bukan backlog opsional pasca-1.0.

## Sasaran V2

V2 diarahkan untuk memenuhi sasaran inti berikut:

- arsitektur scalable dengan boundary yang jelas
- skill system yang modular dan aman untuk produksi
- interface standar: CLI, Telegram, WhatsApp, email, API/webhook
- budget dan token cost control yang fleksibel
- scheduler dan automation rutin yang durable
- personality layer yang konsisten dan tidak tercampur dengan execution
- memory/preference engine yang belajar dari kebiasaan pengguna

## Temuan yang Menggerakkan V2

Fondasi saat ini sudah lebih kuat dari fase awal:

- ada `job_runtime`, `scheduler_runtime`, `execution_history`, `execution_metrics`, dan `admin_api`
- external assets sudah punya trust policy, capability declaration, dan approval state
- job queue sudah dipisah dari planner

Gap arsitektural yang masih tersisa:

- `Assistant` masih memegang terlalu banyak tanggung jawab
- auth/policy transport masih menempel ke core orchestration
- admin API masih bersifat ops read-only, belum ada conversation API standar
- usage token belum naik ke layer budget/cost governance
- personality, planner, lessons, dan memory masih dirakit di satu prompt builder
- external skill yang di-approve masih dieksekusi in-process
- state runtime masih file-based dan belum tahan untuk multi-process/service mode

## Prinsip Desain

- `transport-agnostic core`: semua channel masuk lewat request schema yang sama
- `service boundary first`: auth, planning, memory, policy, dan execution dipisah
- `local-first durable state`: state penting pindah dari flat file ke store durable
- `policy before action`: semua aksi mutatif dan external execution lewat policy/approval service
- `budget-aware AI`: pemilihan model dan konteks ditentukan juga oleh budget, trust, dan latency
- `privacy tiering`: profile, preferences, secrets, dan working memory tidak diperlakukan sama
- `observable automation`: automation background harus punya trace, metrics, queue, dan notification

## Layer Arsitektur V2

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            User / System Channels                           │
│          CLI | Telegram | WhatsApp | Email | API Client | Webhook          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Interface and Identity Layer                          │
│  interfaces/*                                                                │
│  - inbound adapters                                                          │
│  - identity/session resolution                                               │
│  - auth/rate limit/channel policy                                            │
│  - canonical InteractionRequest                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Interaction Services                               │
│  services/interactions/*                                                     │
│  - conversation API                                                          │
│  - command API                                                               │
│  - admin API                                                                 │
│  - notification dispatcher                                                   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Agent Runtime Core                               │
│  services/runtime/*                                                          │
│  - orchestration service                                                     │
│  - planner service                                                           │
│  - execution service                                                         │
│  - scheduler/trigger service                                                 │
│  - policy and approval service                                               │
│  - model router and budget manager                                           │
└───────────────┬──────────────────────────┬──────────────────────────┬───────┘
                │                          │                          │
                ▼                          ▼                          ▼
┌───────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────────────┐
│ Personal Intelligence     │  │ Skill and Tool Runtime    │  │ Observability and Ops    │
│ services/personality/*    │  │ runtime/*                 │  │ observability/*          │
│ services/memory/*         │  │ - built-in skill runtime  │  │ - traces                 │
│ - profile service         │  │ - isolated external skill │  │ - metrics                │
│ - preference service      │  │ - tool adapters           │  │ - audit log              │
│ - memory retrieval/rank   │  │ - integration connectors  │  │ - queue diagnostics      │
└───────────────┬───────────┘  └───────────────┬───────────┘  └──────────────┬───────────┘
                │                              │                              │
                └──────────────┬───────────────┴───────────────┬──────────────┘
                               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Storage Layer                                   │
│  storage/*                                                                    │
│  - state DB (SQLite first, optional Postgres later)                           │
│  - memory index (FTS / vector)                                                │
│  - secrets store                                                              │
│  - workspace boundary                                                         │
│  - audit/event store                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Boundary yang Harus Dipisah

### 1. Interface vs Core Agent

Target:

- semua channel menghasilkan `InteractionRequest`
- auth, pairing, allowlist, rate limit, dan channel-specific policy berhenti tinggal di `Assistant`
- transport tidak menyentuh planner, memory, atau execution logic secara langsung

Implikasi:

- Telegram auth pindah ke `interfaces/telegram/auth.py`
- channel baru seperti WhatsApp dan email tinggal mengikuti contract yang sama

### 2. Personality vs Planner vs Execution

Target:

- `personality service` memegang identity, style, boundaries, dan stable user preferences
- `planner service` memegang goal, task, dependency, retry, blocked reason
- `execution service` hanya fokus pada menjalankan task/skill/tool
- `memory service` bertanggung jawab atas retrieval, consolidation, dan pruning

Implikasi:

- prompt context tidak lagi dibangun oleh satu fungsi yang mencampur semuanya
- prompt assembly menjadi hasil ranking beberapa source yang berbeda

### 3. Policy vs Skill Runtime

Target:

- policy engine memutuskan izin, approval, risk gate, dan redaction
- built-in skill runtime tetap in-process
- external skill runtime dipisah ke isolated worker atau subprocess sandbox

Implikasi:

- approval external skill tidak lagi dianggap cukup tanpa isolation
- audit log bisa membedakan policy decision dan execution result

### 4. Provider Adapter vs Budget Control

Target:

- provider adapter hanya bertugas bicara ke model
- `model router` memilih provider/model berdasarkan trust, latency, dan cost class
- `budget manager` memegang quota, cost estimate, dan fallback policy

Implikasi:

- usage token harus menjadi bagian dari trace standar
- orchestration bisa menurunkan mode reasoning saat budget ketat

## Modul Target

### Interface Layer

- `src/cadiax/interfaces/cli/`
- `src/cadiax/interfaces/telegram/`
- `src/cadiax/interfaces/whatsapp/`
- `src/cadiax/interfaces/email/`
- `src/cadiax/interfaces/api/`

Tanggung jawab:

- ubah event/channel payload menjadi request kanonik
- resolve user identity, session, dan transport metadata
- terapkan auth dan policy dasar per channel

### Runtime Services

- `src/cadiax/services/runtime/orchestrator.py`
- `src/cadiax/services/runtime/planner_service.py`
- `src/cadiax/services/runtime/execution_service.py`
- `src/cadiax/services/runtime/scheduler_service.py`
- `src/cadiax/services/runtime/trigger_service.py`

Tanggung jawab:

- route request ke command, plan, execute, reflect, atau replan
- menjalankan queue, scheduler, dan event trigger internal
- menjaga contract result lintas transport dan automation

### Personal Intelligence

- `src/cadiax/services/personality/profile_service.py`
- `src/cadiax/services/personality/preference_service.py`
- `src/cadiax/services/memory/memory_service.py`
- `src/cadiax/services/memory/retrieval_service.py`
- `src/cadiax/services/memory/consolidation_service.py`

Tanggung jawab:

- menyimpan stable profile dan learned preference
- menyusun working context berdasar ranking, bukan concat mentah
- mendukung habit tracking, consolidation, dan selective recall

### Governance and Safety

- `src/cadiax/services/policy/policy_service.py`
- `src/cadiax/services/policy/approval_service.py`
- `src/cadiax/services/policy/privacy_service.py`
- `src/cadiax/services/policy/external_asset_service.py`

Tanggung jawab:

- action approval
- capability enforcement
- privacy tiering dan redaction
- external manifest validation dan trust policy

### Model and Budget

- `src/cadiax/services/ai/model_router.py`
- `src/cadiax/services/ai/budget_manager.py`
- `src/cadiax/services/ai/context_budgeter.py`

Tanggung jawab:

- memilih provider/model yang tepat
- memotong konteks sesuai budget dan SLA
- menyimpan usage, estimate cost, dan fallback decision

### Runtime Isolation

- `src/cadiax/runtime/builtin/`
- `src/cadiax/runtime/external_runner/`
- `src/cadiax/runtime/connectors/`

Tanggung jawab:

- load built-in skills dengan cepat
- jalankan external skills secara terisolasi
- menjembatani tool/process/network connector sesuai policy

### Observability and Operations

- `src/cadiax/observability/traces.py`
- `src/cadiax/observability/metrics.py`
- `src/cadiax/observability/audit.py`
- `src/cadiax/observability/admin_api.py`

Tanggung jawab:

- trace end-to-end per interaction, task, dan automation cycle
- expose metrics queue, model, tool, dan budget
- menyediakan ops surface yang tetap read-only secara default

## Domain Data dan Penyimpanan

Domain yang perlu dipisah:

- `identity and sessions`
- `profile and preferences`
- `working memory and consolidated memory`
- `goals, plans, jobs, triggers`
- `policies, approvals, trust registry`
- `usage, budget, traces, metrics`
- `channel state and notifications`

Pilihan storage:

- `SQLite` sebagai tahap awal untuk state utama dan audit event
- `FTS` atau vector index lokal untuk memory retrieval
- secret tetap di secure storage yang ada sekarang
- workspace tetap local-first dengan guard terpusat

## Alur Utama V2

### Alur Conversation

1. adapter menerima request dari channel
2. interface layer menormalkan payload menjadi `InteractionRequest`
3. policy layer mengecek auth, redaction, dan permission
4. orchestration memilih direct command, plan/execute, atau AI reasoning
5. memory/personality service menyuplai context ter-ranking
6. execution menghasilkan structured result
7. formatter/transport mengirim respons
8. trace, metrics, usage, dan budget diperbarui

### Alur Automation

1. scheduler/trigger service menerima clock/event signal
2. planner atau queue service memilih job yang siap jalan
3. policy layer mengecek apakah job boleh dijalankan tanpa approval tambahan
4. execution service menjalankan skill/tool
5. result memicu reflect, replan, atau notification
6. observability layer menyimpan trace dan health signal

### Alur External Skill

1. asset di-scan dan manifest divalidasi
2. capability declaration dan approval state dicek
3. execution berjalan di isolated runner
4. structured result dikembalikan ke runtime core
5. audit log menyimpan policy decision dan execution outcome

## Pemetaan Fase Implementasi

### Phase A: Service Boundary dan Control Plane

Target hasil:

- core agent tidak lagi menampung auth transport, scheduler orchestration, dan admin concerns sekaligus
- state runtime pindah ke store durable
- worker/scheduler siap dijalankan sebagai service

Deliverable utama:

- canonical request/response contract
- extraction `interaction gateway`
- SQLite-backed runtime state
- service wrapper untuk worker/scheduler/admin API

### Phase B: Personal Intelligence dan Budget Governance

Target hasil:

- personality layer konsisten
- assistant mulai belajar preference dan habit dengan retrieval yang lebih tepat
- biaya provider bisa dibatasi dan dipantau

Deliverable utama:

- personality/preference service
- semantic retrieval + consolidation
- model router + budget manager
- privacy-aware prompt assembly

### Phase C: Multi-Surface Platform dan Runtime Isolation

Target hasil:

- channel bertambah tanpa menambah coupling ke core
- skill eksternal punya trust boundary yang nyata
- observability siap untuk operasi jangka panjang

Deliverable utama:

- conversational API/webhook
- WhatsApp/email adapters
- isolated external skill runner
- notification/event bus
- richer ops diagnostics

## Urutan Migrasi yang Aman

1. ekstrak schema request/response dan policy transport tanpa mengubah perilaku user-facing
2. pindahkan state planner/job/metrics/scheduler ke storage service
3. pecah `Assistant` menjadi orchestration, policy, dan interaction services
4. propagasikan usage token ke trace/metrics lalu tambahkan budget manager
5. pecah personality/profile/memory builder menjadi service terpisah
6. perkenalkan isolated external runner
7. buka conversational API dan adapter channel tambahan

## Non-Goals V2

V2 tidak perlu langsung menjadi:

- SaaS multi-tenant
- distributed cluster
- fully autonomous agent tanpa approval

Fokusnya tetap: `personal assistant platform` yang local-first, aman, terukur, dan siap tumbuh.
