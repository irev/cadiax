# OtonomAssist

Private AI CLI dengan fondasi otonom yang sekarang sudah mencakup:

- state persisten antar sesi
- personalisasi markdown
- memory dan lessons yang dibaca ulang otomatis
- planner, executor, dan runner untuk loop semi-otonom
- penyimpanan kredensial lokal yang terpisah dari konteks belajar
- setup wizard interaktif untuk first-run dan reconfigure
- doctor/status read-only untuk audit konfigurasi
- structured result + universal formatter lintas skill inti
- secret storage lintas-OS untuk menjaga service utama tetap portable

## Acuan Produk

Dokumen acuan utama terbaru ada di `docs/specs/autonomous_ai_system_spec_extended.md`.

Dokumen pendukung:

- `docs/architecture/ROADMAP.md`: urutan delivery menuju target rilis `v1.1.0`
- `docs/architecture/TARGET_ARCHITECTURE_V2.md`: target boundary dan module architecture
- `docs/architecture/ARCHITECTURE.md`: snapshot arsitektur implementasi saat ini
- `docs/README.md`: indeks dokumentasi repo

Target resmi repo sekarang bergerak pada baseline rilis `v1.1.0`: seluruh fondasi inti stabil ditambah dashboard monitoring opsional dan service wrapper yang lebih lengkap.

## Fondasi yang Sudah Jadi

Tiga lapisan capability yang sekarang sudah terbentuk:

### 1. Core

- `memory`
- `planner`
- `profile`
- `agent-loop`
- `executor`
- `runner`

### 2. Capability

- `workspace`
- `ai`
- `research`

### 3. Governance

- `self-review`
- `secrets`

## Taxonomy Skill Otonom

Selain pembagian `core / capability / governance`, skill sekarang mulai memakai taxonomy yang lebih dekat ke agent otonom populer:

- `planning`
- `memory`
- `knowledge`
- `environment`
- `execution`
- `governance`

Mapping saat ini:

- `planner`, `agent-loop` -> `planning`
- `memory`, `profile` -> `memory`
- `ai`, `research` -> `knowledge`
- `workspace` -> `environment`
- `executor`, `runner` -> `execution`
- `self-review`, `secrets` -> `governance`

Setiap skill juga bisa mendeklarasikan:

- `risk_level`
- `side_effects`
- `requires`
- `idempotency`

Ini dipakai untuk memperkaya konteks routing AI dan audit skill layer.

## Penyimpanan Data

State agent disimpan di:

```text
.otonomassist/
├── memory.jsonl
├── planner.json
├── profile.md
├── lessons.md
├── secrets.json
└── telegram_auth.json
```

Makna file:

- `memory.jsonl`: memori mentah
- `planner.json`: task/goal
- `profile.md`: personalisasi agent
- `lessons.md`: pembelajaran yang dikonsolidasikan
- `secrets.json`: kredensial lokal
- `telegram_auth.json`: allowlist dan request pairing Telegram

`.otonomassist/` sekarang di-ignore oleh git, jadi data lokal dan secret tidak ikut ter-commit.

Di Windows, value secret sekarang disimpan terenkripsi lokal memakai DPAPI sebelum ditulis ke `secrets.json`.
Di Linux/macOS, runtime memakai backend portable berbasis local file key agar service utama tetap bisa berjalan lintas OS.
State JSON penting seperti planner dan secrets sekarang ditulis secara atomik untuk mengurangi risiko file parsial.

## Workspace Boundary

Akses file workspace sekarang dibatasi oleh guard terpusat:

- semua path harus tetap berada di dalam root workspace
- traversal seperti `../..` ke luar workspace ditolak
- symlink yang resolve ke luar workspace di-skip saat traversal
- mode akses workspace default adalah read-only secara kebijakan: `OTONOMASSIST_WORKSPACE_ACCESS=ro`

Konfigurasi:

```bash
OTONOMASSIST_WORKSPACE_ROOT=
OTONOMASSIST_WORKSPACE_ACCESS=ro
```

Default workspace sekarang diarahkan ke folder `workspace/` di root project. Ini menjadi lokasi default untuk file kerja user, skill tambahan, dan aset eksternal yang dikelola di dalam boundary workspace.

Saat ini skill inspeksi file seperti `workspace` dan `self-review file` memakai guard ini.

## Di Mana Kredensial Sebaiknya Disimpan

Untuk kredensial yang ingin dipakai oleh AI/agent:

- simpan di `secrets.json` melalui skill `secrets`
- runtime akan membaca environment variable terlebih dulu, lalu fallback ke `secrets`
- jangan simpan di `memory.jsonl`
- jangan simpan di `lessons.md`
- jangan simpan di `profile.md`

Alasannya:

- `memory`, `lessons`, dan `profile` dipakai sebagai konteks prompt
- `secrets` sengaja dipisahkan agar tidak otomatis masuk ke prompt AI

Untuk pemakaian internal di masa depan, runtime bisa mengambil secret terdekripsi lewat helper internal, tetapi nilainya tetap tidak ditampilkan ke user atau dikirim ke prompt secara default.

Contoh:

```text
assistant: secrets set github_token ghp_xxx
assistant: secrets set openai_api_key sk-...
assistant: secrets set anthropic_api_key sk-ant-...
assistant: secrets import-env
assistant: secrets list
assistant: secrets show github_token
```

`secrets import-env` akan mengimpor credential umum dari environment seperti `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, dan `TELEGRAM_BOT_TOKEN` ke storage terenkripsi lokal tanpa menampilkan nilainya.

## Loop Otonom Saat Ini

Urutan yang sekarang sudah bisa berjalan:

1. `planner` menyimpan task
2. `executor next` menjalankan task berikutnya
3. `self-review` menulis hasil audit ke memory, lessons, dan planner
4. `agent-loop` merefleksikan state agent
5. `runner` dapat menjalankan beberapa langkah berturut-turut atau sampai idle

Stabilisasi yang sudah diterapkan:

- `executor` mengenali prefix native penting seperti `research`, `runner`, dan `secrets`
- task otonom dibatasi agar tidak diam-diam memutasi `secrets` atau `profile`
- `self-review` mendedupe follow-up task terbuka agar backlog tidak meledak
- `runner until-idle` sekarang merefleksikan state setiap langkah
- lesson yang identik di recent window tidak ditulis berulang-ulang

Contoh:

```text
assistant: planner add workspace read README.md
assistant: runner steps 2
assistant: agent-loop next
assistant: ai apa langkah berikutnya berdasarkan seluruh state yang ada?
```

## Skill Aktif

- `ai`
- `memory`
- `planner`
- `profile`
- `agent-loop`
- `executor`
- `runner`
- `workspace`
- `self-review`
- `secrets`
- `research`

## Menjalankan Aplikasi

```bash
pip install -e .
otonomassist setup
otonomassist status
otonomassist chat
```

CLI utama sekarang mendukung subcommand resmi:

- `otonomassist setup`
- `otonomassist status`
- `otonomassist doctor`
- `otonomassist doctor --json`
- `otonomassist config status`
- `otonomassist config setup`
- `otonomassist chat`
- `otonomassist run "<message>"`
- `otonomassist telegram`
- `otonomassist jobs list`
- `otonomassist jobs enqueue`
- `otonomassist worker --steps N`
- `otonomassist worker --until-idle --enqueue-first`
- `otonomassist metrics`
- `otonomassist metrics --json`
- `otonomassist api --host 127.0.0.1 --port 8787`
- `otonomassist conversation-api --host 127.0.0.1 --port 8788`
- `otonomassist service status`
- `otonomassist service show worker --runtime posix`
- `otonomassist service write`
- `otonomassist service run worker --interval 5 --steps 5 --max-loops 0`
- `otonomassist scheduler --cycles 3 --interval 5`
- `otonomassist external audit`
- `otonomassist external sync`
- `otonomassist external install <path-atau-url>`
- `otonomassist external approve <name>`
- `otonomassist external reject <name>`
- `otonomassist skills audit`

`otonomassist setup` menjalankan wizard konfigurasi interaktif untuk initial install atau reconfigure setelah install. Wizard ini meminta konfirmasi eksplisit untuk pilihan sensitif seperti provider, mode akses workspace, dan penyimpanan credential.

`otonomassist status` dan `otonomassist doctor` menampilkan audit konfigurasi read-only: provider aktif, credential tersedia atau tidak, workspace guard, dan status Telegram. Report sekarang juga memberi level `healthy`, `warning`, atau `critical` agar hasil audit lebih cepat dibaca. Di dalam assistant, audit yang sama juga tersedia lewat command `doctor` atau `config status`.

Alias kompatibilitas lama masih didukung sementara:

- `otonomassist --setup`
- `otonomassist --doctor`
- `otonomassist -i`
- `otonomassist <pesan>`

Ekstensi eksternal sekarang diarahkan ke layout workspace:

```text
workspace/
├── skills-external/
├── tools/
└── packages/
```

`otonomassist external audit` atau command assistant `external audit` menampilkan inventaris asset eksternal yang teraudit, kapan terdeteksi/ditambahkan, dan di mana lokasinya.
`otonomassist external sync` memaksa scan ulang `workspace/skills-external` lalu memperbarui registry audit bila ada skill baru atau metadata yang berubah.
`otonomassist external install <path-lokal-atau-url-git>` memasang skill eksternal ke `workspace/skills-external/`, lalu langsung mencatat event audit install dan hasil cek kompatibilitas.

Skill eksternal bisa menambahkan manifest opsional `asset.json` di root skill untuk membantu audit dan cek kompatibilitas. Contoh:

```json
{
  "name": "my-skill",
  "manager": "git",
  "version": "1.0.0",
  "requires": ["git", "python"],
  "capabilities": ["workspace_read"],
  "platforms": ["windows", "linux"]
}
```

Audit akan memakai manifest itu untuk menampilkan:

- siapa/apa yang menambahkan asset
- versi yang dicatat
- requirement toolchain
- capability yang diminta asset
- status kompatibilitas `ready` atau `degraded`
- toolchain yang masih hilang

Policy trust default untuk skill eksternal sekarang adalah `approval-required`. Artinya skill eksternal tetap bisa di-install dan diaudit, tetapi tidak otomatis di-load sampai di-approve.
Approval sekarang juga memerlukan capability declaration yang valid di `asset.json`.
Secara default, capability yang diizinkan untuk skill eksternal hanya `workspace_read`. Capability lain harus dibuka eksplisit lewat:

```bash
OTONOMASSIST_EXTERNAL_CAPABILITY_ALLOW=workspace_read,network
```

Contoh:

```bash
otonomassist external install <path-atau-url-git>
otonomassist external approve my-skill
otonomassist external reject my-skill
```

Jika ingin perilaku lama yang langsung memuat semua skill eksternal, set:

```bash
OTONOMASSIST_EXTERNAL_SKILL_POLICY=allow-all
```

Telegram runner:

```bash
otonomassist telegram
otonomassist-telegram
```

Built-in commands:

```text
help
list
history
metrics
skills audit
doctor
config status
debug-config
list-models
```

## Structured Result dan View

Skill inti sekarang mulai memakai structured result envelope, lalu dirender ulang oleh sistem sesuai permintaan user.

View yang didukung:

- `summary`
- `short`
- `table`
- `markdown`
- `json`

Contoh:

```text
assistant: research siapa presiden saat ini
assistant: research --view json siapa presiden saat ini
assistant: workspace cari README dalam bentuk tabel
assistant: memory summary informasi singkat
```

Jadi penyajian hasil tidak lagi harus ditanam di masing-masing skill; skill bisa fokus menghasilkan data yang stabil, lalu formatter mengubah presentasinya.

Skill yang sudah memakai structured result sebagai jalur utama:

- `research`
- `workspace`
- `planner`
- `memory` untuk operasi baca utama
- `self-review`

## Konfigurasi OpenAI

Simpan API key di `secrets` bila memungkinkan, dan gunakan `.env` untuk konfigurasi non-secret seperti provider, model, dan base URL.

Contoh secret:

```text
assistant: secrets set openai_api_key sk-...
```

Contoh `.env`:

```bash
AI_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
OPENAI_FALLBACK_MODEL=gpt-4o
OPENAI_WEB_MODEL=gpt-4.1
```

Wizard setup akan menulis nilai non-secret ke `.env`, lalu menawarkan penyimpanan credential ke encrypted local secrets agar miss-config lebih kecil dan secret tidak tersebar ke file konteks lain.

## Telegram Ke Depan

Fondasi Telegram sekarang sudah tersedia lewat long polling.

Konfigurasi:

```bash
TELEGRAM_OWNER_IDS=
TELEGRAM_DM_POLICY=pairing
TELEGRAM_ALLOW_FROM=
TELEGRAM_GROUP_POLICY=allowlist
TELEGRAM_GROUPS=
TELEGRAM_GROUP_ALLOW_FROM=
TELEGRAM_REQUIRE_MENTION=true
TELEGRAM_OWNER_ONLY_PREFIXES=debug-config,list-models,secrets,executor,runner
TELEGRAM_APPROVED_PREFIXES=help,list,ai,research,memory,planner,profile,agent-loop,workspace,self-review
```

Simpan token bot melalui `secrets` bila memungkinkan:

```text
assistant: secrets set telegram_bot_token <token>
```

Lalu jalankan:

```bash
otonomassist-telegram
```

Policy authorization Telegram sekarang fail-closed:

- DM default memakai `TELEGRAM_DM_POLICY=pairing`
- user baru harus DM `/pair` untuk membuat request akses
- owner yang ada di `TELEGRAM_OWNER_IDS` dapat meninjau request dengan `/auth pending`
- owner dapat approve/reject dengan `/auth approve <request_id>` atau `/auth reject <request_id>`
- grup hanya dilayani jika chat ada di allowlist dan, untuk `allowlist`, pengirimnya juga ada di allowlist user
- di grup, bot hanya merespons bila di-mention atau saat membalas pesan bot bila `TELEGRAM_REQUIRE_MENTION=true`
- user `approved` tidak otomatis punya hak penuh; prefix sensitif seperti `secrets`, `executor`, `runner`, `debug-config`, dan `list-models` default-nya owner-only
- daftar prefix owner-only dan prefix yang boleh untuk user `approved` bisa diatur lewat `TELEGRAM_OWNER_ONLY_PREFIXES` dan `TELEGRAM_APPROVED_PREFIXES`
- di dalam prefix yang diizinkan pun ada gate aksi:
  - `workspace tree|read|find|files|summary` boleh untuk `approved`
  - `memory list|search|get|summarize|context` boleh, tetapi `memory add|remember|consolidate` owner-only
  - `planner list|next|summary` boleh, tetapi `planner add|set-goal|done|blocked|note|clear` owner-only
  - `profile show` boleh, tetapi semua operasi ubah profile owner-only
  - `self-review` dan `agent-loop` dibatasi untuk owner karena menulis kembali ke state pembelajaran

State authorization Telegram disimpan lokal di:

```text
.otonomassist/telegram_auth.json
```

Semua pesan Telegram tetap masuk ke jalur yang sama dengan CLI melalui `Assistant.handle_message(...)`, jadi loop agent inti tidak perlu diubah.

Jika tetap ingin memakai environment variable, `TELEGRAM_BOT_TOKEN` masih didukung sebagai fallback.

## Validasi Fakta Real-World

OtonomAssist sekarang memiliki skill `research` untuk pertanyaan yang sensitif terhadap:

- tanggal
- jadwal/libur
- informasi terbaru
- fakta dunia nyata yang bisa berubah

Pada provider OpenAI, skill ini memakai web-grounded lookup sebelum menjawab. Selain itu, `Assistant` juga memiliki heuristic yang akan langsung memaksa query seperti:

- `kapan idul fitri 2026`
- `buat rencana libur idul fitri 2026`
- `siapa presiden saat ini`

melewati jalur `research`, bukan menjawab dari model chat biasa.

Output `research` sekarang distabilkan sebagai data terstruktur dengan metadata verifikasi, lalu dapat dirender ulang ke summary/table/json sesuai permintaan user.

## Kualitas dan Test

Suite test sekarang mencakup area yang paling riskan untuk operasi lebih serius:

- stabilitas loop `planner -> executor -> runner -> self-review`
- formatter universal di level `Assistant`
- authorization Telegram
- failure path AI provider
- setup wizard dan doctor/status

Fondasi observability minimum juga mulai aktif:

- setiap command inbound sekarang punya `trace_id`
- event inti seperti `command_received`, `skill_started`, `skill_completed`, dan `command_completed` ditulis ke `.otonomassist/execution_history.jsonl`
- operator bisa melihat jejak terbaru lewat `otonomassist history`
- operator bisa melihat agregat metrik lewat `otonomassist metrics`
- timeout skill global bisa diatur dengan `OTONOMASSIST_SKILL_TIMEOUT_SECONDS`
- `doctor/status` sekarang juga mendukung output machine-readable lewat `--json`
- report `doctor/status` sekarang juga memiliki section `[Runtime]` untuk queue worker
- admin API read-only lokal tersedia untuk `/health`, `/status`, `/metrics`, `/jobs`, dan `/history`
- jika `OTONOMASSIST_ADMIN_TOKEN` diisi, admin API memerlukan header `X-OtonomAssist-Token` atau `Authorization: Bearer ...`

Fondasi runtime Phase 2 juga mulai aktif:

- planner task sekarang bisa membawa `priority`, `depends_on`, `retry_count`, dan `blocked_reason`
- `planner next` sekarang memilih task `ready` berdasarkan dependency dan priority
- runtime job queue lokal disimpan di `.otonomassist/job_queue.json`
- command `jobs` dan `worker` memberi lapisan eksplisit antara planner dan executor
- worker sekarang bisa berjalan `until-idle` dan mencatat `last_worker_run_at` / `last_worker_status`
- context orchestration sekarang mulai memanfaatkan retrieval memori relevan berbasis token overlap, bukan recency-only
- scheduler runtime sekarang tersedia untuk menjalankan cycle worker berkala dan mencatat state terakhir ke `.otonomassist/scheduler_state.json`

Perubahan ini membuat fondasi saat ini lebih layak dipakai sebagai sistem semi-otonom yang konsisten, bukan hanya eksperimen skill per skill.

## Arsitektur

Lihat [ARCHITECTURE.md](/d:/PROJECT/otonomAssist/docs/architecture/ARCHITECTURE.md) untuk alur detail runtime, storage, dan loop semi-otonom.

Untuk panduan install, first-run, reconfigure, audit config, operasi semi-otonom, dan troubleshooting cepat, lihat [OPERATIONS.md](/d:/PROJECT/otonomAssist/OPERATIONS.md).

Untuk jejak perubahan fitur yang sudah mendarat, lihat [CHANGELOG.md](/d:/PROJECT/otonomAssist/CHANGELOG.md). Untuk arah implementasi berikutnya, lihat [ROADMAP.md](/d:/PROJECT/otonomAssist/docs/architecture/ROADMAP.md) yang sekarang dibagi ke:

- `Phase 1: Semi-Production Hardening`
- `Phase 2: Autonomous Runtime`
- `Phase 3: Production Agent Platform`

## Transport Ke Depan

Entry point pesan sekarang sudah dipisahkan lewat `Assistant.handle_message(...)`, sehingga CLI hanyalah salah satu transport. Ini sengaja disiapkan agar input ke depan bisa datang dari Telegram atau chat transport lain tanpa mengubah loop agent inti.
