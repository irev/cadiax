# Arsitektur Cadiax

## Tujuan

Fondasi `Private AI` yang otonom dan stateful di workspace lokal, cukup kuat untuk mendukung tiga lapisan skill:

- `core`
- `capability`
- `governance`

## Tiga Lapisan Skill

### Core

- `memory`
- `planner`
- `profile`
- `agent-loop`
- `executor`
- `runner`

### Capability

- `workspace`
- `ai`
- `research`

### Governance

- `self-review`
- `secrets`

## Taxonomy Skill Layer Otonom

Selain pembagian `core / capability / governance`, runtime sekarang mulai memakai taxonomy skill-layer yang lebih dekat ke pola agent otonom populer. Tujuannya agar orchestrator dapat menilai bukan hanya nama skill, tetapi juga jenis aksi, risiko, dan kebutuhannya.

Enam kategori yang dipakai:

- `planning`: skill untuk memecah tujuan, memilih langkah, dan menentukan prioritas
- `memory`: skill untuk menyimpan identitas, konteks, dan jejak pembelajaran
- `knowledge`: skill untuk reasoning umum dan pencarian/validasi pengetahuan
- `environment`: skill untuk membaca atau menjelajah lingkungan kerja lokal
- `execution`: skill yang benar-benar menindaklanjuti task atau menjalankan loop
- `governance`: skill untuk audit, safety, secret handling, dan kontrol risiko

Mapping saat ini:

- `planning`: `planner`, `agent-loop`
- `memory`: `memory`, `profile`
- `knowledge`: `ai`, `research`
- `environment`: `workspace`
- `execution`: `executor`, `runner`
- `governance`: `self-review`, `secrets`

## Diagram Sistem

```text
┌──────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                               │
│                     src/cadiax/cli.py                          │
│  - setup / status / doctor / chat / run / worker / scheduler        │
│  - metrics / api / telegram                                         │
│  - compatibility alias: --setup / --doctor / -i / raw message       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Transport Adapters                           │
│  CLI -> Assistant.handle_message(...)                                │
│  Telegram -> Assistant.handle_message(...)                           │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Setup + Config Audit Layer                        │
│  src/cadiax/core/setup_wizard.py                               │
│  src/cadiax/core/config_doctor.py                              │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          Assistant Layer                             │
│                 src/cadiax/core/assistant.py                   │
│  - load .env                                                         │
│  - fallback ke local secrets untuk credential runtime                │
│  - ensure .cadiax storage                                      │
│  - ensure default workspace root exists                              │
│  - load skills                                                       │
│  - inject persistent context into prompts                            │
│  - route direct command / AI fallback / forced research              │
│  - record execution history + execution metrics                      │
│  - pilih view presentasi hasil                                       │
│  - format structured result untuk user                               │
│  - apply Telegram role-based authorization gate                      │
└───────────────┬───────────────────────┬───────────────────────────────┘
                │                       │
                ▼                       ▼
┌──────────────────────────────┐   ┌───────────────────────────────────┐
│        Skill Runtime         │   │         AI Provider Layer         │
│  registry + loader           │   │         OpenAI, etc.              │
└───────────────┬──────────────┘   └───────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Runtime Control Plane + Ops Surface                  │
│  execution_history / execution_metrics / job_runtime                 │
│  scheduler_runtime / admin_api / external_assets                     │
└───────────────┬──────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Result Builder + Formatter                        │
│  src/cadiax/core/result_builder.py                             │
│  src/cadiax/core/result_formatter.py                           │
└───────────────┬──────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          Skill Layers                                │
│  core -> capability -> governance                                    │
└───────────────┬──────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Persistent Agent Storage                       │
│  .cadiax/profile.md                                            │
│  .cadiax/lessons.md                                            │
│  .cadiax/planner.json                                          │
│  .cadiax/memory.jsonl                                          │
│  .cadiax/secrets.json                                          │
│  .cadiax/telegram_auth.json                                    │
│  .cadiax/job_queue.json                                        │
│  .cadiax/execution_history.jsonl                               │
│  .cadiax/execution_metrics.json                                │
│  .cadiax/scheduler_state.json                                  │
│  .cadiax/external_assets.json                                  │
└──────────────────────────────────────────────────────────────────────┘
```

## Loop Otonom Saat Ini

Loop yang sudah berjalan:

```text
planner -> executor -> memory
            ↓
         self-review
            ↓
      lessons + follow-up task
            ↓
        agent-loop reflect/next
            ↓
      runner menjalankan beberapa langkah
```

Artinya:

- task dapat disimpan
- task dapat dieksekusi
- hasil eksekusi dapat disimpan kembali
- hasil review dapat membuat task lanjutan
- agent dapat memberi langkah berikutnya berdasarkan state lokal

Stabilisasi loop yang sudah diterapkan:

- planner/secrets state penting ditulis atomik
- `executor` mengenali lebih banyak prefix native agar tidak terlalu bergantung pada fallback AI
- task otonom yang mutatif terhadap `secrets` dan `profile` diblok di jalur executor planner-task
- `self-review` mendedupe follow-up task terbuka
- `runner until-idle` menjalankan refleksi di setiap langkah, konsisten dengan mode steps
- lesson berulang didedupe di recent window

## Structured Result Pipeline

Runtime sekarang memakai pola:

```text
skill producer -> structured result envelope -> formatter -> transport/user
```

Prinsipnya:

- skill fokus menghasilkan data kanonik
- `Assistant` mendeteksi preferensi presentasi user
- formatter mengubah data ke `summary`, `short`, `table`, `markdown`, atau `json`
- transport tidak perlu membentuk ulang data dari nol

Ini membuat skill lebih mudah dirangkai untuk otomasi dan lebih konsisten lintas CLI/Telegram.

## Result Envelope Contract

Structured result lintas skill memakai bentuk umum:

```json
{
  "type": "research_result",
  "status": "ok",
  "data": {},
  "meta": {
    "source_skill": "research",
    "default_view": "summary"
  }
}
```

Makna field:

- `type`: tipe domain hasil, misalnya `research_result`, `planner_list`, `workspace_find`
- `status`: status hasil, biasanya `ok` atau `degraded`
- `data`: payload utama yang relevan untuk skill
- `meta.source_skill`: nama skill asal
- `meta.default_view`: view bawaan jika user tidak meminta format eksplisit

Field meta tambahan boleh ditambahkan bila perlu, misalnya `verification_status`.

## Skill Capability Contract

Setiap skill sekarang bisa mendeklarasikan metadata tambahan di `SKILL.md`:

- `autonomy_category`
- `risk_level`
- `side_effects`
- `requires`
- `idempotency`

Contoh:

```text
## Metadata
- name: workspace
- category: capability
- autonomy_category: environment
- risk_level: medium
- side_effects: [workspace_read]
- requires: [workspace_access]
- idempotency: idempotent
```

Kontrak ini dipakai untuk:

- memperkaya konteks routing AI di `Assistant`
- audit skill layer via command `skills audit`
- memberi fondasi policy executor yang lebih granular ke depan
- membantu skill eksternal menyatakan requirement dan risiko secara eksplisit

## View Presentation

Formatter saat ini mendukung view:

- `summary`
- `short`
- `table`
- `markdown`
- `json`

Pemilihan view bisa terjadi lewat:

- flag eksplisit seperti `--view table`
- intent natural language seperti `dalam bentuk tabel`, `informasi singkat`, atau `format json`
- default view dari envelope hasil

Bagian ini dikerjakan oleh:

- [result_builder.py](/d:/PROJECT/otonomAssist/src/cadiax/core/result_builder.py)
- [result_formatter.py](/d:/PROJECT/otonomAssist/src/cadiax/core/result_formatter.py)
- [assistant.py](/d:/PROJECT/otonomAssist/src/cadiax/core/assistant.py)

Skill inti yang sudah mengikuti pola ini:

- `research`
- `workspace`
- `planner`
- `memory` untuk read path utama
- `self-review`

## Persistent Context

Modul [agent_context.py](/d:/PROJECT/otonomAssist/src/cadiax/core/agent_context.py) adalah inti persistence.

Ia menangani:

- bootstrap file
- profile markdown
- lessons markdown
- planner json
- memory jsonl
- secrets json
- atomic write untuk planner/secrets
- helper update task / note / lesson / memory

Konteks yang otomatis masuk ke prompt:

- `profile.md`
- `lessons.md`
- planner summary
- recent memories

Yang tidak masuk ke prompt:

- `secrets.json`
- `telegram_auth.json`

Secret di `secrets.json` sekarang disimpan terenkripsi lokal di Windows memakai DPAPI.

## Workspace Sandbox Policy

Untuk operasi file, arsitektur sekarang memakai boundary workspace terpusat:

- root workspace berasal dari `CADIAX_WORKSPACE_ROOT` atau default ke `workspace/` di root project
- path absolut dan relatif di-resolve lalu divalidasi agar tetap berada di bawah workspace root
- traversal ke luar workspace ditolak
- symlink yang mengarah ke luar workspace diabaikan saat enumerasi
- mode akses kebijakan disiapkan lewat `CADIAX_WORKSPACE_ACCESS`, default `ro`

Ini penting agar inspeksi file oleh AI tetap terbatas pada workspace lokal yang diizinkan.

Pilihan ini juga menjaga agar skill/asset eksternal tambahan yang dipasang user dapat terkonsentrasi di area kerja yang jelas, terpisah dari state internal `.cadiax`.

## Penyimpanan Kredensial

Kredensial user sebaiknya disimpan di:

```text
.cadiax/secrets.json
```

dan dikelola lewat skill `secrets`.

Prinsipnya:

- simpan secret terpisah dari memory/lessons/profile
- runtime membaca env lebih dulu, lalu fallback ke `secrets`
- jangan injeksikan secret ke prompt AI secara default
- tampilkan hanya fingerprint, bukan value
- ignore file ini dari git

Ini penting karena `memory`, `lessons`, dan `profile` memang dibaca ulang untuk pembelajaran; secret tidak boleh ikut tercampur di sana.

Wizard setup menulis konfigurasi non-secret ke `.env`, lalu menawarkan penyimpanan credential ke encrypted local secrets untuk mengurangi miss-config.

Backend secrets sekarang dibagi menurut platform:

- Windows: DPAPI user-scoped
- Linux/macOS: portable encrypted file key

Tujuannya adalah menjaga contract runtime tetap sama untuk skill dan service utama, walau treatment backend berbeda per OS.

## Setup dan Config Audit

Layer konfigurasi sekarang dibagi dua:

- `setup_wizard.py`
  - first-run / reconfigure interaktif
  - memilih provider
  - menetapkan workspace root dan mode akses
  - menawarkan penyimpanan credential ke secrets lokal
  - mengatur Telegram dasar
- `config_doctor.py`
  - audit read-only
  - memberi status `healthy`, `warning`, atau `critical`
  - mengecek provider, credential, workspace, Telegram, dan storage

Entry point CLI resmi:

- `cadiax setup`
- `cadiax status`
- `cadiax doctor`
- `cadiax config status`
- `cadiax config setup`
- `cadiax chat`
- `cadiax run "<message>"`
- `cadiax worker`
- `cadiax scheduler`
- `cadiax metrics`
- `cadiax api`
- `cadiax telegram`

## Platform Layer

Fondasi lintas-OS sekarang mulai dipisahkan ke layer platform:

- `src/cadiax/platform/process_manager.py`
- `src/cadiax/platform/service_runtime.py`
- `src/cadiax/platform/toolchain.py`

Perannya:

- mendeskripsikan strategi runtime per OS
- menjaga service utama tidak hardcode Windows-only atau Linux-only
- memberi contract untuk ekspansi supervisor/service manager berikutnya
- memberi audit awal untuk toolchain eksternal seperti `git`, `python`, `pip`, `node`, dan `npm`

Status saat ini:

- process dan service runtime sudah punya abstraction
- supervisor/background daemon penuh belum diimplementasikan
- `doctor/status` sekarang menampilkan capability layer ini agar gap platform terlihat eksplisit

## Control Plane dan Runtime Automation

Fondasi operasional yang sekarang sudah ada:

- `execution_history.py`: trace dan event history untuk command, skill, dan task
- `execution_metrics.py`: agregasi counter/timing untuk operator dan admin API
- `job_runtime.py`: leasing, completion, dan ringkasan queue worker
- `scheduler_runtime.py`: cycle scheduler foreground yang menulis state scheduler
- `admin_api.py`: local read-only API untuk `health`, `status`, `metrics`, `jobs`, `scheduler`, dan `history`
- `external_assets.py`: trust policy, capability declaration, dan approval state untuk asset eksternal

## Telegram Authorization Policy

Transport Telegram sekarang memakai policy fail-closed yang cocok untuk private AI:

- DM default: `pairing`
- grup default: `allowlist`
- owner Telegram didefinisikan di `TELEGRAM_OWNER_IDS`
- user DM baru harus meminta akses dengan `/pair`
- owner menyetujui lewat `/auth approve <request_id>`
- grup harus ada di allowlist dan, untuk policy `allowlist`, pengirim juga harus di allowlist
- mention atau reply-to-bot dapat diwajibkan lewat `TELEGRAM_REQUIRE_MENTION=true`
- setelah lolos authorization transport, message masih melewati gate role-based di `Assistant`
- prefix sensitif default seperti `secrets`, `executor`, `runner`, `debug-config`, dan `list-models` dibatasi untuk owner Telegram
- gate kedua ini juga memeriksa level aksi/subcommand, bukan hanya nama skill
- akibatnya, `planner list` dapat diizinkan untuk user `approved`, sementara `planner add` tetap owner-only
- transport Telegram dan `Assistant` sekarang sudah punya regression coverage untuk branch non-owner, unapproved, pairing prompt, dan owner-only prefix

State authorization Telegram disimpan terpisah di:

```text
.cadiax/telegram_auth.json
```

File ini bukan bagian dari memory pembelajaran. Tujuannya murni untuk kontrol akses transport.

## Skill Roles

### `memory`

- raw event store
- search/summarize
- consolidation ke `lessons.md`
- read operation utama sekarang dapat menghasilkan structured result

### `planner`

- backlog
- status task
- next task
- read operation utama sekarang dapat menghasilkan structured result

### `profile`

- personalization markdown
- purpose, preferences, constraints, long-term context

### `executor`

- ambil task `todo`
- resolve command
- eksekusi lewat `Assistant`
- update `planner`, `memory`, `lessons`

### `runner`

- jalankan `executor` beberapa langkah
- cocok untuk mode autopilot terbatas

### `self-review`

- audit heuristik
- tulis hasil ke memory
- tulis lesson
- buat follow-up task
- hasil audit sekarang juga dipresentasikan sebagai structured result

### `secrets`

- set/list/show/delete credential lokal
- aman dari prompt injection otomatis
- value disimpan encrypted-at-rest

### `research`

- validasi fakta real-world yang sensitif terhadap waktu
- web-grounded lookup sebelum menjawab
- dipakai untuk tanggal, jadwal, libur, dan informasi terbaru
- hasil riset dirender ulang sesuai view yang diminta user

## Tahap Fundamental yang Sudah Selesai

Bagian yang sudah bisa dianggap fondasi selesai:

- skill system aktif dan fokus ke private AI
- persistence antar sesi
- retrieval ulang untuk prompt berikutnya
- profile markdown personalization
- lessons markdown learning
- planner/executor/runner chain
- governance layer dasar lewat self-review dan secrets

## Batas Saat Ini

Yang belum selesai:

- `Assistant` masih menjadi titik konsentrasi orchestration, transport policy, dan command routing
- scheduler masih foreground loop; supervisor daemon/service wrapper belum siap produksi
- admin API masih surface operasional read-only, belum conversational API atau webhook platform
- budget/cost control dan model routing belum ada
- personality, planner, dan memory retrieval masih terlalu rapat; retrieval baru lexical/token overlap
- external skill yang sudah di-approve masih berjalan in-process, belum lewat isolated runtime
- Telegram masih long polling, belum webhook
- web-grounded research saat ini paling kuat pada provider OpenAI

## Langkah Berikut yang Logis

- ekstraksi `interaction/policy` dari `Assistant` ke service boundary terpisah
- migrasi state planner/job/metrics/scheduler ke storage yang lebih durable
- personality dan preference service yang dipisah dari planner/execution
- model router + budget manager + token usage tracing
- isolated external skill runner
- conversational API dan adapter channel tambahan

Target state detail untuk fase berikutnya ada di `docs/architecture/TARGET_ARCHITECTURE_V2.md`.
