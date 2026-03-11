# Autonomous Personal AI Assistant — System Specification (Extended)

## 1. Vision
Membangun AI otonom personal assistant yang modular, scalable, cost-aware, memiliki skill management terstandar, multi-channel communication interface, scheduler untuk tugas rutin, personality yang konsisten, serta kemampuan memahami preferensi dan kebiasaan pengguna secara aman dan terkontrol.

## 1.1 Konteks untuk OtonomAssist

Dokumen ini adalah spesifikasi sistem utama dan menjadi source of truth terbaru untuk arah produk OtonomAssist.

Jika ada perbedaan antara dokumen ini dengan dokumen lain, maka dokumen ini yang menjadi acuan utama. Dokumen lain berfungsi sebagai turunan implementasi, breakdown fase, atau snapshot arsitektur saat ini.

Dokumen ini disejajarkan dengan:

- `ROADMAP.md`
- `ARCHITECTURE.md`
- `TARGET_ARCHITECTURE_V2.md`

Posisi implementasi repo saat ini:

- fondasi `scheduler`, `admin API`, `execution metrics`, `execution history`, dan `external approval` sudah ada
- sistem berada di akhir fondasi `Autonomous Runtime` dan mulai masuk `Production Agent Platform`
- gap utama yang masih perlu ditutup adalah durable state, service boundary, token budget governance, personality separation, dan runtime isolation

Dokumen ini dipakai sebagai system spec yang lebih luas dari sekadar arsitektur kode. Tujuannya adalah menerjemahkan visi produk, modular boundary, operational constraints, dan fase implementasi ke dalam bentuk yang bisa dipakai untuk pengembangan jangka panjang.

## 1.2 Target Release

GOAL resmi repo:

- seluruh capability dan boundary yang didefinisikan di dokumen ini merupakan scope target `v1.0.0`
- tidak ada bagian inti dari spesifikasi ini yang diposisikan sebagai `post-1.0`
- roadmap, target architecture, dan breakdown implementasi harus diturunkan dari target `v1.0.0` tersebut

Konsekuensinya, `v1.0.0` harus mencakup paling tidak:

- skill system modular dan terstandar
- multi-channel communication interface yang direncanakan
- scheduler dan automation rutin
- personality layer yang terpisah dan konsisten
- memory, preference, dan habit understanding yang aman
- token cost control dan model routing
- observability, audit, policy, dan privacy controls yang layak produksi

---

## 2. Architecture Principles
- Modular architecture
- Separation of concerns
- Replaceable components (LLM, memory, interface)
- Deterministic skill execution
- Privacy-first design
- Observability and logging
- Cost-aware inference
- Safe automation boundaries

---

## 3. Core Modules
1. Interface Layer
2. Event Normalizer
3. Orchestrator
4. Planner
5. Skill Registry
6. Execution Engine
7. Memory System
8. Scheduler
9. Personality Layer
10. Observability & Security

---

## 4. Production-Grade Autonomous AI Architecture Diagram

```text
┌──────────────────────────────────────────────────────────────┐
│                    COMMUNICATION INTERFACES                 │
│   CLI | Telegram | WhatsApp | Email | REST API | Dashboard │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────┐
│                     EVENT NORMALIZER                        │
│  normalize message, source, user_id, session_id, metadata   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR CORE                       │
│ intent routing | policy check | session state | mode select │
└───────────────┬───────────────────────┬─────────────────────┘
                │                       │
                v                       v
┌──────────────────────────┐   ┌──────────────────────────────┐
│      PERSONALITY ENGINE  │   │        PLANNER ENGINE        │
│ tone | style | relation  │   │ goals | tasks | priorities   │
│ boundaries | preferences │   │ plan | retry | reflection    │
└──────────────┬───────────┘   └──────────────┬───────────────┘
               │                              │
               └──────────────┬───────────────┘
                              v
┌──────────────────────────────────────────────────────────────┐
│                    EXECUTION ENGINE                         │
│ skill select | validation | timeout | retry | audit log     │
└───────────────┬──────────────────────────────────────────────┘
                │
                v
┌──────────────────────────────────────────────────────────────┐
│                       SKILL REGISTRY                        │
│ web | email | whatsapp | calendar | file | code | database │
│ each skill has schema, policy, timeout, permissions         │
└───────────────┬──────────────────────────────────────────────┘
                │
                v
┌──────────────────────────────────────────────────────────────┐
│                     EXTERNAL SYSTEMS                        │
│ Browser | Email | WhatsApp | Calendar | Files | APIs | DB  │
└──────────────────────────────────────────────────────────────┘

                              ^
                              │
┌──────────────────────────────────────────────────────────────┐
│                        MEMORY LAYER                         │
│ vector memory | episodic memory | preference memory         │
│ summaries | retrieval | pruning | user controls             │
└──────────────────────────────────────────────────────────────┘

                              ^
                              │
┌──────────────────────────────────────────────────────────────┐
│                    TOKEN COST OPTIMIZER                     │
│ model routing | summarization | cache | top-k control       │
│ iteration limit | context budget | fallback model           │
└──────────────────────────────────────────────────────────────┘

                              ^
                              │
┌──────────────────────────────────────────────────────────────┐
│                     SCHEDULER / AUTOMATION                  │
│ daily jobs | recurring tasks | triggers | reminders         │
│ monitoring | retries | escalation                           │
└──────────────────────────────────────────────────────────────┘

                              ^
                              │
┌──────────────────────────────────────────────────────────────┐
│                 OBSERVABILITY & SECURITY                    │
│ logs | traces | metrics | secret management | sandbox       │
│ prompt injection defense | permission policy                │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Struktur Folder Project Agent

```text
autonomous-ai/
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ configs/
│  ├─ app.yaml
│  ├─ models.yaml
│  ├─ scheduler.yaml
│  └─ policies.yaml
├─ apps/
│  ├─ cli/
│  │  └─ main.py
│  ├─ api/
│  │  └─ main.py
│  ├─ telegram/
│  │  └─ bot.py
│  ├─ whatsapp/
│  │  └─ webhook.py
│  └─ dashboard/
│     └─ app.py
├─ src/
│  ├─ core/
│  │  ├─ orchestrator.py
│  │  ├─ event_normalizer.py
│  │  ├─ session_manager.py
│  │  ├─ policy_engine.py
│  │  └─ types.py
│  ├─ planner/
│  │  ├─ planner.py
│  │  ├─ goal_manager.py
│  │  ├─ task_queue.py
│  │  ├─ reflection.py
│  │  └─ heuristics.py
│  ├─ execution/
│  │  ├─ executor.py
│  │  ├─ dispatcher.py
│  │  ├─ timeout.py
│  │  ├─ retry.py
│  │  └─ sandbox.py
│  ├─ skills/
│  │  ├─ registry.py
│  │  ├─ base.py
│  │  ├─ web_search/
│  │  │  ├─ SKILL.md
│  │  │  ├─ handler.py
│  │  │  ├─ schema.py
│  │  │  └─ tests.py
│  │  ├─ send_email/
│  │  │  ├─ SKILL.md
│  │  │  ├─ handler.py
│  │  │  ├─ schema.py
│  │  │  └─ tests.py
│  │  └─ ...
│  ├─ memory/
│  │  ├─ manager.py
│  │  ├─ vector_store.py
│  │  ├─ episodic_store.py
│  │  ├─ preference_store.py
│  │  ├─ summarizer.py
│  │  ├─ retriever.py
│  │  └─ pruning.py
│  ├─ personality/
│  │  ├─ engine.py
│  │  ├─ profile.py
│  │  ├─ rules.py
│  │  └─ adaptation.py
│  ├─ scheduler/
│  │  ├─ service.py
│  │  ├─ jobs.py
│  │  ├─ triggers.py
│  │  ├─ recurrence.py
│  │  └─ policies.py
│  ├─ cost/
│  │  ├─ optimizer.py
│  │  ├─ model_router.py
│  │  ├─ budget.py
│  │  ├─ cache.py
│  │  └─ compression.py
│  ├─ llm/
│  │  ├─ provider.py
│  │  ├─ prompts/
│  │  ├─ model_client.py
│  │  └─ tool_calling.py
│  ├─ integrations/
│  │  ├─ email/
│  │  ├─ whatsapp/
│  │  ├─ telegram/
│  │  ├─ calendar/
│  │  └─ browser/
│  ├─ security/
│  │  ├─ secrets.py
│  │  ├─ permissions.py
│  │  ├─ injection_guard.py
│  │  └─ validators.py
│  └─ observability/
│     ├─ logger.py
│     ├─ tracing.py
│     ├─ metrics.py
│     └─ audit.py
├─ storage/
│  ├─ sqlite/
│  ├─ qdrant/
│  ├─ files/
│  └─ logs/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
└─ docs/
   ├─ architecture.md
   ├─ skills.md
   ├─ memory.md
   └─ operations.md
```

### Catatan desain
- `apps/` hanya adapter interface, bukan business logic utama.
- `src/core/` berisi alur sistem.
- `skills/` wajib modular, terisolasi, dan memiliki schema.
- `memory/`, `scheduler/`, `cost/`, `personality/` dipisah agar tidak saling menumpuk.

---

## 6. Standar Desain Skill (SKILL.md Format)

Setiap skill sebaiknya memiliki file `SKILL.md` yang seragam agar mudah dipahami agent, Codex, dan developer.

### Template `SKILL.md`

```md
# Skill: send_email

## 1. Purpose
Mengirim email ke penerima tertentu dengan subjek dan isi pesan.

## 2. When to Use
- Saat agent perlu mengirim notifikasi formal
- Saat user meminta follow-up email
- Saat scheduler menjalankan routine report

## 3. When Not to Use
- Jika hanya perlu membuat draft
- Jika alamat email belum tervalidasi
- Jika policy melarang outbound email

## 4. Inputs
- recipient: string, email wajib valid
- subject: string
- body: string
- cc: list[string], optional
- attachments: list[string], optional

## 5. Output
- status: success | failed
- message_id: string | null
- error: string | null

## 6. Dependencies
- SMTP provider / email API
- secret manager
- permission policy

## 7. Execution Policy
- timeout: 15s
- retry: 2x
- idempotent: false
- requires_confirmation: optional
- audit_log: required

## 8. Security Constraints
- Jangan kirim ke domain yang diblok
- Jangan kirim attachment sensitif tanpa izin
- Validasi input terhadap injection/header abuse

## 9. Failure Handling
- Jika timeout, retry
- Jika auth gagal, hentikan dan log critical
- Jika recipient invalid, return failed tanpa retry

## 10. Example Input
```json
{
  "recipient": "user@example.com",
  "subject": "Laporan Harian",
  "body": "Berikut ringkasan hari ini"
}
```

## 11. Example Output
```json
{
  "status": "success",
  "message_id": "mail_12345",
  "error": null
}
```
```

### Standar wajib untuk semua skill
- Nama unik
- Purpose jelas
- Input schema eksplisit
- Output schema eksplisit
- Dependency list
- Timeout
- Retry policy
- Security constraints
- Failure handling
- Example input/output

### Kontrak skill yang baik
- **Deterministic** bila memungkinkan
- **Stateless** bila memungkinkan
- **Observable** selalu
- **Permission-aware** wajib
- **Composable** mudah dirangkai dengan skill lain

---

## 7. Arsitektur Memory (Vector + Episodic + Preference)

Memory sebaiknya dibagi menjadi tiga lapisan utama.

### 7.1 Vector Memory
Untuk pencarian semantik dari pengetahuan dan dokumen.

**Isi**
- dokumen
- hasil riset
- catatan
- ringkasan percakapan panjang
- knowledge chunks

**Fungsi**
- retrieval by similarity
- knowledge augmentation
- referensi jangka panjang

**Teknologi umum**
- Qdrant
- FAISS
- Chroma

### 7.2 Episodic Memory
Untuk menyimpan pengalaman dan kejadian.

**Isi**
- aksi agent yang pernah dijalankan
- hasil task
- kegagalan sebelumnya
- keputusan penting
- histori interaksi yang bermakna

**Fungsi**
- belajar dari pengalaman
- menghindari pengulangan kesalahan
- referensi tindakan sebelumnya

**Storage umum**
- SQLite
- Postgres
- JSON log terstruktur

### 7.3 Preference Memory
Untuk preferensi dan kebiasaan pengguna.

**Isi**
- channel favorit
- gaya komunikasi
- jam aktif
- prioritas kerja
- rutinitas umum
- topik yang sering diminta

**Fungsi**
- personalisasi
- adaptive scheduling
- response tuning
- proactive assistance

**Storage umum**
- relational DB / key-value store

### Diagram memory

```text
                 ┌────────────────────────┐
                 │      MEMORY MANAGER    │
                 └───────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        v                    v                    v
┌───────────────┐    ┌───────────────┐    ┌────────────────┐
│ VECTOR MEMORY │    │ EPISODIC MEM. │    │ PREFERENCE MEM │
│ semantic docs │    │ events/actions│    │ user habits    │
│ embeddings    │    │ outcomes      │    │ preferences    │
└───────┬───────┘    └───────┬───────┘    └───────┬────────┘
        │                    │                    │
        └──────────────┬─────┴────────────┬──────┘
                       v                  v
               ┌────────────────────────────────┐
               │ RETRIEVAL + SUMMARIZATION      │
               │ rank | filter | merge | prune  │
               └────────────────────────────────┘
```

### Retrieval policy
1. Cek preference memory untuk personal context cepat
2. Cek episodic memory untuk tindakan/kejadian relevan
3. Cek vector memory untuk knowledge semantik
4. Merge hasil
5. Ringkas sebelum masuk ke context LLM

### Prinsip penting
- Jangan masukkan semua memory ke prompt
- Terapkan top-k retrieval
- Simpan summary berkala
- Sediakan user control: view, edit, delete memory

---

## 8. Desain Planner Agent

Planner bertugas mengubah tujuan menjadi langkah kerja yang bisa dieksekusi.

### Komponen planner
- Goal parser
- Task decomposer
- Priority scorer
- Dependency resolver
- Skill selector
- Retry strategy
- Reflection loop

### Alur planner

```text
User goal / scheduled goal
        ↓
Goal parser
        ↓
Task decomposition
        ↓
Priority scoring
        ↓
Dependency resolution
        ↓
Skill selection
        ↓
Execution request
        ↓
Result evaluation
        ↓
Replan / finish
```

### Jenis planner
1. **Rule-based planner**  
   cepat, murah, cocok untuk tugas rutin.
2. **LLM-based planner**  
   fleksibel, cocok untuk tugas kompleks.
3. **Hybrid planner**  
   paling realistis untuk production.

### Struktur task ideal
```json
{
  "task_id": "task_001",
  "goal_id": "goal_001",
  "name": "check important emails",
  "priority": "high",
  "depends_on": [],
  "candidate_skills": ["search_email", "summarize_email"],
  "timeout_sec": 30,
  "retry_limit": 2,
  "status": "pending"
}
```

### Aturan planner yang sehat
- batasi jumlah iterasi
- batasi kedalaman decomposition
- gunakan heuristic untuk tugas rutin
- replan hanya jika hasil gagal/ambigu
- log alasan pemilihan skill

### Output planner
- ordered task list
- required skills
- execution constraints
- stop conditions
- memory update instructions

---

## 9. Workflow Scheduler Harian

Scheduler bertugas menjalankan tugas rutin dan monitoring.

### Contoh workflow harian

```text
06:30  Generate morning context
07:00  Check calendar today
07:15  Check important email
08:00  Send morning briefing
12:00  Midday summary / urgent pending items
17:30  Review unfinished tasks
20:00  Check unread messages
21:00  Prepare tomorrow summary
```

### Flow scheduler

```text
Trigger time / event
       ↓
Load job definition
       ↓
Policy check
       ↓
Planner generate task
       ↓
Execution engine run skills
       ↓
Store results in memory
       ↓
Send notification / summary
       ↓
Log success or failure
```

### Komponen scheduler
- recurrence engine
- event trigger
- priority queue
- retry manager
- quiet hours policy
- escalation rules

### Contoh job definition
```yaml
job_id: daily_email_check
schedule: "0 7 * * *"
timezone: "Asia/Jakarta"
enabled: true
goal: "Check important email and summarize high priority items"
priority: high
max_runtime_sec: 180
retry_limit: 2
quiet_hours_respect: true
```

### Kebijakan scheduler yang penting
- hormati jam tenang user
- punya retry terbatas
- pisahkan job harian vs event-driven
- simpan audit log
- jangan kirim notifikasi berlebihan

---

## 10. Arsitektur Token Cost Optimizer

Tujuan cost optimizer adalah mengendalikan biaya tanpa merusak kualitas.

### Komponen
- Model router
- Prompt budget manager
- Retrieval limiter
- Summarization cache
- Response cache
- Iteration limiter
- Fallback model policy

### Diagram

```text
Input Task
   ↓
Complexity Classifier
   ↓
Model Router ────────────────┐
   ↓                         │
Context Budget Manager       │
   ↓                         │
Memory Retriever (top-k)     │
   ↓                         │
Prompt Compressor            │
   ↓                         │
LLM Call                     │
   ↓                         │
Cost Logger <────────────────┘
```

### Strategi utama
1. **Model routing**  
   - small model: klasifikasi, ekstraksi, ringkasan pendek  
   - medium model: planning ringan  
   - large model: reasoning kompleks, keputusan penting

2. **Selective retrieval**  
   - ambil hanya memory relevan
   - batasi top-k
   - skip retrieval bila task sederhana

3. **Context compression**  
   - ringkas histori panjang
   - ubah hasil lama jadi summary
   - pakai structured context, bukan raw transcript

4. **Caching**
   - cache hasil retrieval
   - cache summary harian
   - cache prompt template

5. **Loop limits**
   - batasi iterasi planner
   - batasi retry LLM
   - timeout per task

### Policy contoh
```yaml
token_policy:
  low_cost_mode:
    planner_model: small
    executor_model: small
    max_context_tokens: 4000
    retrieval_top_k: 3
    max_iterations: 3

  balanced_mode:
    planner_model: medium
    executor_model: medium
    max_context_tokens: 8000
    retrieval_top_k: 5
    max_iterations: 5

  high_accuracy_mode:
    planner_model: large
    executor_model: large
    max_context_tokens: 16000
    retrieval_top_k: 8
    max_iterations: 7
```

---

## 11. Arsitektur Personality Engine

Personality engine membuat AI konsisten, personal, tetapi tetap aman.

### Tujuan
- konsistensi tone
- adaptasi ke preferensi user
- batas perilaku yang jelas
- menjaga identitas assistant

### Komponen
- Personality profile
- Style rules
- Relationship context
- Preference adapter
- Safety boundaries
- Response policy

### Diagram

```text
User Input
   ↓
Intent Analysis
   ↓
Personality Engine
   ├─ tone selection
   ├─ preference adaptation
   ├─ relationship context
   └─ boundary enforcement
   ↓
Response / Action framing
   ↓
Orchestrator / LLM
```

### Isi personality profile
- nama assistant
- gaya bicara default
- formalitas
- tingkat proaktif
- aturan batas komunikasi
- humor tolerance
- preferred brevity
- escalation tone

### Yang boleh dipersonalisasi
- cara menyapa
- panjang respons
- formal/santai
- kapan proaktif
- channel favorit
- jenis ringkasan yang disukai

### Yang jangan dicampur
- personality ≠ planner
- personality ≠ policy security
- personality ≠ psychological diagnosis

### Prinsip aman
- jangan manipulatif
- jangan membuat inferensi psikologis sensitif tanpa izin
- personalisasi harus bisa direset user
- preferensi harus dapat diedit/hapus

---

## 12. Non-Functional Requirements

### Reliability
- skill timeout
- retry terbatas
- graceful failure
- idempotency untuk skill aman

### Scalability
- skill registry modular
- interface adapters terpisah
- storage backend dapat diganti
- LLM provider abstraction

### Security
- secret manager
- permission per skill
- audit log
- prompt injection filtering
- sandbox untuk eksekusi kode

### Observability
- structured logging
- tracing per goal/task
- cost metrics
- scheduler status
- failure dashboard

### Privacy
- memory visibility untuk user
- delete/export control
- minimization principle
- consent-based personalization

---

## 13. Roadmap Implementasi untuk Repo Ini

### Posisi saat ini
- CLI dan Telegram sudah aktif
- scheduler foreground, worker queue, dan admin API sudah ada
- skill trust policy dan approval external asset sudah ada
- metrics dan execution history dasar sudah ada
- semantic memory, budget manager, conversation API, WhatsApp, email, dan isolated external runtime belum selesai

### Phase A — Service Boundary dan Durable Runtime
- Pisahkan `interface`, `policy`, dan `orchestration` dari core agent monolitik
- Migrasikan planner, job queue, metrics, scheduler state, dan audit event ke storage durable
- Bangun `conversation API` yang terpisah dari `admin API`
- Tambahkan service wrapper untuk worker, scheduler, dan API
- Satukan trace backend untuk interaction, job, task, dan automation cycle

Target fase ini:
- arsitektur lebih scalable
- communication interface tidak lagi melekat ke core orchestration
- scheduler siap dipakai sebagai runtime service, bukan sekadar command foreground

### Phase B — Personality, Memory, dan Cost-Aware Intelligence
- Pisahkan `personality service`, `planner service`, dan `execution service`
- Tambahkan `preference store`, `habit model`, dan `semantic retrieval`
- Terapkan `context ranking` dan `memory consolidation`
- Propagasikan token usage ke trace dan metrics
- Bangun `model router`, `budget manager`, dan `context budgeter`
- Tambahkan privacy-aware prompt assembly dan redaction policy

Target fase ini:
- personality konsisten dan tidak tercampur dengan planner/security
- sistem mulai memahami preferensi dan kebiasaan user secara aman
- biaya provider remote bisa dikontrol sesuai mode penggunaan

### Phase C — Multi-Channel Platform dan Runtime Isolation
- Tambahkan interface `WhatsApp`, `email`, `event/webhook`, dan `notification dispatcher`
- Pindahkan external skill ke `isolated runner` atau subprocess sandbox
- Tambahkan event bus internal untuk trigger dan automation
- Perluas observability ke queue depth, provider latency, cost metrics, approval audit, dan policy diagnostics
- Tambahkan cross-channel continuity berbasis identity/session layer

Target fase ini:
- platform siap berkembang ke multi-surface personal assistant
- skill system lebih aman dan layak produksi
- automation rutin bisa dijalankan dan dipantau dalam jangka panjang

### Phase D — Advanced Personal Assistant Maturity
- Episodic learning yang lebih matang
- Rekomendasi dan proactive assistance yang kontekstual
- Quiet hours, consent boundary, dan user-control layer yang lebih kaya
- Personal knowledge graph atau structured preference profile
- Long-term privacy governance untuk export/delete/retention

Target fase ini:
- assistant memahami kebiasaan user tanpa kehilangan kontrol, privasi, atau auditability
- sistem siap menjadi personal assistant yang benar-benar berkelanjutan

### Dependency order yang direkomendasikan
1. durable state + service boundary
2. personality and memory separation
3. token usage tracing + budget manager
4. external runtime isolation
5. channel expansion dan proactive automation

---

## 14. Checklist Validasi Cepat

- Apakah interface terpisah dari core agent?
- Apakah skill punya schema, timeout, dan retry?
- Apakah memory dipisah jadi vector, episodic, dan preference?
- Apakah planner punya limit iterasi?
- Apakah scheduler hormati quiet hours?
- Apakah token budget bisa diatur?
- Apakah token usage masuk ke trace dan metrics?
- Apakah personality dipisah dari security/policy?
- Apakah personality dipisah dari planner dan execution?
- Apakah external skill berjalan terisolasi dari runtime utama?
- Apakah semua eksekusi punya log dan audit trail?
- Apakah user bisa mengontrol memorinya?
- Apakah sistem siap berkembang tanpa tight coupling?
