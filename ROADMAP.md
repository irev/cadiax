# Roadmap

Roadmap ini memetakan evolusi OtonomAssist dari fondasi semi-otonom yang sudah ada menuju autonomous agent platform yang lebih matang.

Fokusnya dibagi ke tiga fase:

- `Phase 1: Semi-Production Hardening`
- `Phase 2: Autonomous Runtime`
- `Phase 3: Production Agent Platform`

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

- akhir fondasi `task automation agent`
- awal `semi-production hardening`

Artinya, prioritas terdekat tetap:

1. observability minimum
2. execution safety
3. planner/runtime maturation

Sebelum masuk agresif ke scheduler dan autonomy background penuh.
