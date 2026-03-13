# Roadmap

Roadmap ini memetakan evolusi Cadiax dari fondasi semi-otonom yang sudah ada menuju autonomous agent platform yang lebih matang.

Dokumen acuan utama sekarang adalah `docs/specs/autonomous_ai_system_spec_extended.md`.

Jika ada perbedaan arah antara roadmap ini dan spec tersebut, maka spec yang menjadi referensi utama. Roadmap ini berfungsi sebagai urutan delivery untuk mencapai target rilis `v1.0.0`.

## Target Release v1.0.0

Target resmi `v1.1.1` adalah menuntaskan seluruh capability inti yang didefinisikan pada `docs/specs/autonomous_ai_system_spec_extended.md`, termasuk:

- arsitektur modular dan scalable
- skill management terstandar
- communication interfaces utama
- scheduler dan automation rutin
- personality layer yang konsisten
- preference dan habit understanding yang aman
- token cost control
- observability, privacy, dan security boundary yang layak produksi

Baseline maturity roadmap tetap dibagi ke tiga fase:

- `Phase 1: Semi-Production Hardening`
- `Phase 2: Autonomous Runtime`
- `Phase 3: Production Agent Platform`

Untuk eksekusi target `v1.0.0`, breakdown implementasi operasional memakai `Phase A-D` di bagian bawah dokumen ini.

Prinsip umum:

- pertahankan kompatibilitas jalur yang sudah stabil
- perubahan loop otonom wajib punya regression test
- keamanan dan auditability didahulukan sebelum autonomy yang lebih agresif
- skill baru sebaiknya mengikuti structured result dan capability metadata

## Phase 1: Semi-Production Hardening

Tujuan fase ini adalah membuat sistem aman, terukur, dan stabil untuk penggunaan rutin internal.

### Outcome

- eksekusi lebih aman dan bisa diaudit
- failure tidak silent
- loop semi-otonom tidak mudah macet atau liar
- service utama tetap ringan dan kompatibel lintas OS

### Deliverables

- `execution history` terstruktur untuk:
  - command
  - skill
  - task
  - status
  - duration
  - error type
- logging terstruktur lintas:
  - assistant
  - executor
  - runner
  - telegram transport
  - external installer
- timeout global untuk skill/provider/process yang berjalan terlalu lama
- retry policy dasar dengan klasifikasi:
  - transient
  - blocked
  - permanent
- policy executor berbasis metadata skill:
  - `risk_level`
  - `autonomy_category`
  - `idempotency`
- sandbox/policy lebih ketat untuk external skills
- output `doctor/status` machine-readable seperti JSON

### Dependency Order

1. execution log + trace id
2. timeout controller
3. error classification + retry policy
4. executor policy engine
5. doctor JSON + ops audit

### Komponen Checklist yang Ditutup

- tool timeout
- tool retry mechanism
- timeout controller
- logging
- action tracing
- error tracking
- execution history
- permission system lintas skill
- prompt injection protection dasar

### Risiko

- terlalu banyak guard bisa membuat agent terasa pasif
- retry tanpa klasifikasi yang baik bisa mengulang error permanen

## Phase 2: Autonomous Runtime

Tujuan fase ini adalah menaikkan sistem dari task automation agent menjadi runtime otonom yang lebih goal-driven.

### Outcome

- goal tidak lagi hanya field pasif di planner
- task bisa diprioritaskan dan direplan
- worker bisa berjalan tanpa trigger manual terus-menerus
- memory yang masuk ke prompt jadi lebih relevan

### Deliverables

- `goal manager` sebagai entitas runtime terpisah dari backlog
- planner yang mendukung:
  - task decomposition
  - priority
  - dependency
  - retry count
  - blocked reason
  - replan state
- `job queue` terpisah dari planner state
- `scheduler/worker` untuk menjalankan loop berkala
- event trigger internal:
  - task selesai
  - task gagal
  - review selesai
  - memory threshold
- semantic memory retrieval
- context ranking sebelum prompt injection
- memory pruning/consolidation policy
- reasoning loop eksplisit:
  - plan
  - execute
  - reflect
  - replan

### Dependency Order

1. planner schema baru
2. job queue runtime
3. scheduler/worker
4. semantic retrieval
5. explicit replan loop

### Komponen Checklist yang Ditutup

- goal manager
- task planner yang lebih nyata
- job queue
- scheduler
- event triggers
- vector embedding
- memory retrieval
- memory pruning
- context window control yang lebih matang
- reasoning strategy yang lebih eksplisit

### Risiko

- planner yang terlalu kompleks bisa menurunkan determinisme
- worker background tanpa observability akan sulit dioperasikan

## Phase 3: Production Agent Platform

Tujuan fase ini adalah menjadikan sistem layak sebagai platform agent, bukan hanya CLI agent lokal.

### Outcome

- operasi multi-surface lebih rapi
- plugin/tool eksternal lebih aman
- observability cukup untuk operasi jangka panjang
- autonomy bisa dikelola sebagai service

### Deliverables

- API/admin interface untuk:
  - status
  - trace lookup
  - job inspection
  - policy diagnostics
- metrics dasar:
  - task latency
  - tool latency
  - provider latency
  - success/failure rate
  - queue depth
- advanced sandbox untuk external tools/skills
- trust model untuk external assets:
  - source
  - manifest validation
  - capability declaration
  - approval state
- transport expansion:
  - Telegram webhook opsional
  - event/webhook interface
- model routing policy:
  - low-cost
  - high-trust
  - web-grounded
- budget/cost control untuk provider remote

### Dependency Order

1. metrics + trace backend
2. admin/API layer
3. external skill trust policy
4. advanced sandbox/runtime isolation
5. multi-surface service operations

### Komponen Checklist yang Ditutup

- API interface
- metrics
- production observability
- sandbox execution yang lebih penuh
- tool/toolchain governance

### Risiko

- menambah banyak surface area operasional
- biaya integrasi meningkat jika remote model routing dibuka luas

## Cross-Cutting Workstreams

Workstream ini berjalan lintas fase.

### 1. Security

- prompt injection hardening
- capability-based executor policy
- external skill trust and approval
- secret handling audit

### 2. Cross-Platform Runtime

- service runtime Windows/Linux
- process manager abstraction yang lebih nyata
- capability reporting per OS
- degradasi fitur yang eksplisit jika backend belum setara

### 3. Skill Contract Standardization

- result envelope untuk skill baru
- capability metadata:
  - `autonomy_category`
  - `risk_level`
  - `side_effects`
  - `requires`
  - `idempotency`
- schema yang lebih eksplisit untuk skill eksternal

### 4. Testing

- regression test loop otonom
- failure path provider/tool/transport
- persistence corruption/recovery
- scheduler/background tests
- external skill install/trust policy tests

## Definition of Done per Fase

### Phase 1 selesai jika:

- setiap eksekusi penting punya history dan trace
- timeout/retry dasar aktif
- command berisiko tinggi tunduk pada policy
- ops bisa audit sistem tanpa membaca file state mentah

### Phase 2 selesai jika:

- goal dapat dipecah dan direplan
- worker dapat menjalankan loop tanpa trigger manual
- memory retrieval tidak lagi hanya recency-based
- planner dan job runtime terpisah jelas

### Phase 3 selesai jika:

- service dapat dioperasikan dan dipantau sebagai platform
- external tools/skills punya trust boundary yang jelas
- observability cukup untuk operasi berkelanjutan

## Status Saat Ini

Posisi repo saat ini paling tepat berada di antara:

- akhir fondasi `Phase 2: Autonomous Runtime`
- awal `Phase 3: Production Agent Platform`

Artinya, prioritas terdekat tetap:

1. ekstraksi service boundary dan control plane runtime
2. personality, memory, dan budget control yang lebih eksplisit
3. sandbox, isolation, dan ekspansi multi-surface

Scheduler, admin API, metrics dasar, dan external approval sudah ada. Yang belum selesai adalah durability, separation of concerns, cost governance, dan isolation.

## Pemetaan Fase Lanjutan Menuju V2

Dokumen target detail untuk fase berikutnya ada di `docs/architecture/TARGET_ARCHITECTURE_V2.md`.

Phase A-D di bawah ini adalah breakdown implementasi langsung dari `docs/specs/autonomous_ai_system_spec_extended.md` untuk menuntaskan scope `v1.1.1`.

### Phase A: Service Boundary dan Durable Runtime

Assessment:

- `Assistant` masih terlalu sentral untuk routing, auth/policy transport, dan orchestration control.
- runtime queue, scheduler, metrics, dan history sudah ada, tetapi state masih file-based dan belum durable untuk multi-process.

Evaluasi terhadap tujuan:

- menutup target `skalabilitas arsitektur`
- menutup target `communication interface terpisah dari core agent`
- menutup target `scheduler dan automation rutin` pada level service runtime, bukan hanya CLI loop

Modul jangka panjang:

- `interaction gateway`
- `transport policy service`
- `conversation API`
- `state store` durable berbasis SQLite lebih dulu
- `trace backend` yang menyatukan history, metrics, dan job state
- `service supervisor wrapper`

Risks:

- race condition state lokal
- kompleksitas tetap menumpuk di `Assistant`
- background automation sulit dipantau bila tetap bergantung pada foreground process

Roadmap jangka panjang:

1. ekstrak auth/policy transport dari `Assistant`
2. migrasikan planner/job/metrics/scheduler ke store durable
3. pisahkan admin API, conversation API, dan worker service secara eksplisit
4. tambahkan wrapper supervisor lintas OS

### Phase B: Personality, Memory, dan Cost-Aware Intelligence

Assessment:

- personality masih tergabung dengan planner dan execution context
- retrieval memory baru token-overlap, belum semantic/personal preference aware
- provider usage sudah tersedia di adapter, tetapi belum dipakai untuk budget control

Evaluasi terhadap tujuan:

- menutup target `personality layer yang konsisten`
- menutup target `assistant memahami preferensi dan kebiasaan pengguna`
- menutup target `efisiensi biaya token secara fleksibel`

Modul jangka panjang:

- `personality service`
- `preference profile store`
- `semantic memory index`
- `context ranking service`
- `model router`
- `budget manager`
- `privacy/redaction policy`

Risks:

- prompt membengkak dan identitas agent jadi tidak konsisten
- preferensi user tercampur dengan planning state
- biaya provider remote tidak terkendali
- data personal terlalu mudah ikut terkirim ke model

Roadmap jangka panjang:

1. pisahkan profile, preference, dan working memory
2. tambahkan retrieval semantik + ranking
3. propagasikan usage token ke trace dan metrics
4. bangun routing model berbasis biaya, trust, dan latency
5. terapkan redaction/classification sebelum prompt assembly

### Phase C: Platform Expansion dan Safe Extensibility

Assessment:

- channel operasional masih terbatas pada CLI, Telegram, dan admin API read-only
- external skill yang approved masih berjalan in-process
- observability sudah ada, tetapi belum cukup untuk operasi platform jangka panjang

Evaluasi terhadap tujuan:

- menutup target `communication interface standar`
- menutup target `skill system modular, scalable, production-ready`
- menutup target `automation jangka panjang yang bisa dioperasikan sebagai platform`

Modul jangka panjang:

- `webhook/event API`
- adapter `WhatsApp`
- adapter `email`
- `notification dispatcher`
- `isolated external skill runner`
- `approval workflow` lintas asset dan action
- `event bus` internal

Risks:

- privilege escalation dari external skill
- surface area operasional melebar lebih cepat dari governance
- integrasi channel baru memperbesar kompleksitas support dan monitoring

Roadmap jangka panjang:

1. tambahkan runtime isolation untuk skill eksternal
2. bangun outbound/inbound adapter framework lintas channel
3. tambahkan event bus untuk automation dan notification
4. perluas admin/ops surface ke observability yang siap operasi berkelanjutan

### Phase D: Advanced Personal Assistant Maturity

Assessment:

- sistem belum punya episodic learning yang matang, structured habit model, atau cross-channel continuity yang kuat
- privacy controls sudah mulai ada di secrets dan policy dasar, tetapi belum menjadi governance penuh untuk retention, export, delete, dan consent-driven personalization

Evaluasi terhadap tujuan:

- menutup target `assistant pribadi yang memahami preferensi dan kebiasaan pengguna`
- menutup target `personality layer yang konsisten` pada level jangka panjang
- menutup target `personal assistant` yang benar-benar berkelanjutan, bukan sekadar agent task runner

Modul jangka panjang:

- `episodic learning service`
- `habit model`
- `personal knowledge graph`
- `consent and retention policy`
- `cross-channel continuity service`
- `user memory controls`

Risks:

- personalisasi yang agresif dapat melampaui ekspektasi privasi user
- model habit/preference dapat menjadi bias atau salah inferensi
- kompleksitas data lifecycle meningkat saat memory menjadi lebih kaya

Roadmap jangka panjang:

1. tambahkan consent-aware preference learning
2. bangun episodic learning dan habit modeling
3. sediakan export/delete/retention controls untuk memory personal
4. tambah continuity lintas channel berbasis identity/session layer
5. validasi bahwa personalization tetap tunduk pada policy, audit, dan user override
