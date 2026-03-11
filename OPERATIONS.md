# Operations Guide

Panduan ini fokus ke operasi harian OtonomAssist:

- install
- first-run
- reconfigure
- audit konfigurasi
- menjalankan mode chat dan mode semi-otonom
- Telegram
- troubleshooting cepat

## Install

```bash
pip install -e .
```

Verifikasi command utama tersedia:

```bash
otonomassist status
```

## First-Run

Jalankan wizard interaktif:

```bash
otonomassist setup
```

Wizard akan membantu:

- memilih AI provider
- mengatur workspace root
- mengatur mode akses workspace `ro` atau `rw`
- menyimpan credential ke encrypted local secrets
- mengatur Telegram dasar bila diperlukan

Untuk default yang aman:

- workspace access: `ro`
- credential: simpan ke `secrets`
- Telegram DM policy: `pairing`

Default workspace sekarang adalah:

```text
workspace/
```

Gunakan folder ini sebagai lokasi kerja utama dan tempat penyimpanan aset/skill tambahan yang ingin dikelola di dalam boundary workspace.

## Audit Konfigurasi

Untuk melihat status konfigurasi:

```bash
otonomassist status
```

Alias yang setara:

```bash
otonomassist doctor
otonomassist config status
otonomassist doctor --json
```

Di dalam assistant/chat mode:

```text
doctor
config status
```

Makna status:

- `healthy`: konfigurasi inti terlihat aman
- `warning`: sistem berjalan, tetapi ada konfigurasi berisiko atau perlu perhatian
- `critical`: ada masalah yang bisa menghambat operasi inti

Untuk automation atau audit oleh tool lain, gunakan output JSON:

```bash
otonomassist doctor --json
otonomassist status --json
```

Section `[Platform]` di report membantu menilai kesiapan lintas-OS:

- `secret_backend`
- `process_manager`
- `service_runtime`

Saat ini bagian itu dipakai untuk menunjukkan apakah runtime masih foreground-only atau sudah siap ke service/supervisor yang lebih formal.

Section `[Toolchains]` dipakai untuk melihat kesiapan ekosistem skill eksternal:

- `git`
- `python`
- `pip`
- `node`
- `npm`

Ini penting bila nanti skill tambahan dipasang dari git repo, package Python, atau package Node.

Section `[External Assets]` dipakai untuk audit aset eksternal di dalam workspace:

- jumlah asset yang sudah tercatat
- jumlah event install/update yang pernah direkam
- jumlah asset dengan kompatibilitas `degraded`
- lokasi `skills-external/`, `tools/`, dan `packages/`

Contoh temuan umum:

- provider remote belum punya API key
- workspace root tidak ada
- workspace mode `rw`
- Telegram token ada tetapi `TELEGRAM_OWNER_IDS` kosong

## Reconfigure

Untuk mengubah konfigurasi setelah install:

```bash
otonomassist setup
```

atau:

```bash
otonomassist config setup
```

Wizard akan menulis nilai non-secret ke `.env` dan menawarkan update credential di `secrets`.

## Chat dan Single Command

Mode chat interaktif:

```bash
otonomassist chat
```

Alias kompatibilitas:

```bash
otonomassist -i
```

Menjalankan satu pesan langsung:

```bash
otonomassist run "list"
otonomassist run "research siapa presiden saat ini"
otonomassist run "workspace cari README dalam bentuk tabel"
```

Alias kompatibilitas lama:

```bash
otonomassist list
otonomassist research siapa presiden saat ini
```

Audit taxonomy skill layer:

```bash
otonomassist skills audit
```

Command ini membantu melihat kategori skill otonom, risk level, idempotency, requirement, dan side effect yang sudah dideklarasikan oleh skill aktif.

Runtime job queue:

```bash
otonomassist jobs list
otonomassist jobs enqueue
otonomassist worker --steps 1 --enqueue-first
otonomassist worker --steps 10 --until-idle --enqueue-first
otonomassist worker --steps 5 --until-idle --enqueue-first --max-cycles 3 --interval 2
otonomassist scheduler --cycles 3 --interval 5 --steps 5
```

Ini berguna bila Anda ingin memisahkan tahap `task ready` dari planner dan `job execution` di runtime worker.
Section `[Runtime]` pada `status/doctor` sekarang juga menunjukkan ringkasan queue dan aktivitas worker terakhir.

Lihat jejak eksekusi terbaru:

```bash
otonomassist history
```

Command ini membaca event dari `.otonomassist/execution_history.jsonl` dan menampilkan ringkasan eksekusi terbaru beserta `trace_id`.

Lihat metrik agregat runtime:

```bash
otonomassist metrics
otonomassist metrics --json
```

Command ini membaca agregat dari `.otonomassist/execution_metrics.json` untuk melihat volume command/skill, timeout, error, dan timing rata-rata.

Timeout skill global bisa diatur lewat:

```bash
OTONOMASSIST_SKILL_TIMEOUT_SECONDS=60
```

Jika sebuah skill melewati batas ini, assistant akan mengembalikan error timeout dan event history akan ditandai `status=timeout`.

Admin API read-only lokal:

```bash
otonomassist api --host 127.0.0.1 --port 8787
```

Endpoint yang tersedia:

- `/health`
- `/status`
- `/metrics`
- `/jobs`
- `/scheduler`
- `/history?limit=20`

Jika `OTONOMASSIST_ADMIN_TOKEN` diisi, sertakan salah satu:

- header `X-OtonomAssist-Token: <token>`
- header `Authorization: Bearer <token>`

## Asset Eksternal

Layout default untuk asset tambahan yang dikelola user atau AI:

```text
workspace/
├── skills-external/
├── tools/
└── packages/
```

Audit asset eksternal:

```bash
otonomassist external install <path-lokal-atau-url-git>
otonomassist external sync
otonomassist external audit
otonomassist external approve <name>
otonomassist external reject <name>
```

Di dalam assistant:

```text
external install <path-lokal-atau-url-git>
external sync
external audit
```

Jika sebuah skill eksternal ingin mendeklarasikan metadata audit dan requirement, buat `asset.json` di root skill:

```json
{
  "name": "contoh-skill",
  "manager": "git",
  "version": "1.0.0",
  "requires": ["git", "python"],
  "capabilities": ["workspace_read"],
  "platforms": ["windows", "linux"]
}
```

Field ini membantu sistem menilai:

- requirement toolchain yang dibutuhkan
- capability yang diminta asset
- apakah platform saat ini didukung
- apakah asset siap dipakai atau masih `degraded`
- siapa/apa yang terakhir menyinkronkan atau menambahkan asset itu ke registry audit

Secara default, skill eksternal memakai policy `approval-required`:

- skill bisa di-install
- skill masuk audit registry
- skill belum di-load sampai di-approve
- approval akan ditolak jika capability declaration belum valid

Untuk mode yang lebih longgar:

```bash
OTONOMASSIST_EXTERNAL_SKILL_POLICY=allow-all
```

Capability yang diizinkan default hanya `workspace_read`. Jika asset membutuhkan capability lain, buka eksplisit melalui:

```bash
OTONOMASSIST_EXTERNAL_CAPABILITY_ALLOW=workspace_read,network
```

## Operasi Semi-Otonom

Contoh alur dasar:

```text
planner add workspace read README.md
planner add memory add catatan penting
runner steps 2
```

Command inti:

- `planner ...`: kelola goal dan task
- `executor next`: jalankan task todo berikutnya
- `runner once`: jalankan satu langkah
- `runner steps N`: jalankan beberapa langkah
- `runner until-idle`: jalankan sampai backlog todo habis
- `agent-loop reflect`: refleksi state
- `agent-loop next`: usulkan langkah berikutnya
- `self-review ...`: audit hasil atau input tertentu

Catatan operasional:

- gunakan workspace `ro` bila hanya inspeksi/read
- ubah ke `rw` hanya bila memang ingin memberi kemampuan modifikasi file
- task otonom tertentu yang menyentuh `secrets` dan `profile` diblok untuk mencegah perubahan sensitif otomatis
- kegagalan transient seperti timeout/provider error sekarang bisa dijadwalkan ulang otomatis oleh `executor` sampai batas retry task
- worker runtime bisa dipakai untuk memproses queue secara bertahap atau sampai idle tanpa memakai `runner`
- konteks prompt agent sekarang mulai menarik memori yang relevan terhadap command saat orchestration, bukan hanya memory terbaru

## Structured Result dan View

Beberapa skill inti mendukung tampilan universal:

- `summary`
- `short`
- `table`
- `markdown`
- `json`

Contoh:

```text
research --view json siapa presiden saat ini
workspace cari README dalam bentuk tabel
memory summary informasi singkat
```

Skill yang saat ini paling siap untuk pola ini:

- `research`
- `workspace`
- `planner`
- `memory` untuk operasi baca
- `self-review`

## Secrets

Untuk menyimpan credential:

```text
secrets set openai_api_key sk-...
secrets set anthropic_api_key sk-ant-...
secrets set telegram_bot_token <token>
secrets import-env
secrets list
```

Prinsip:

- simpan secret di `secrets`, bukan di memory/profile/lessons
- runtime akan baca env dulu, lalu fallback ke `secrets`
- di Windows, secret disimpan dengan DPAPI
- di Linux/macOS, secret disimpan dengan portable encrypted file key

## Telegram

Menjalankan transport Telegram:

```bash
otonomassist telegram
```

Alias lama masih tersedia:

```bash
otonomassist-telegram
```

Syarat minimal:

- token bot tersedia di `secrets` atau `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_IDS` terisi

Rekomendasi default:

- `TELEGRAM_DM_POLICY=pairing`
- `TELEGRAM_GROUP_POLICY=allowlist`
- `TELEGRAM_REQUIRE_MENTION=true`

Operasi pairing:

1. user DM bot dengan `/pair`
2. owner cek `/auth pending`
3. owner approve dengan `/auth approve <request_id>`

## File Penting

State lokal utama:

```text
.otonomassist/
├── memory.jsonl
├── planner.json
├── job_queue.json
├── profile.md
├── lessons.md
├── secrets.json
├── execution_history.jsonl
├── execution_metrics.json
├── scheduler_state.json
└── telegram_auth.json
```

Konfigurasi non-secret:

```text
.env
```

## Troubleshooting

`status` menunjukkan `critical` pada AI provider

- pastikan `AI_PROVIDER` benar
- simpan API key ke `secrets`
- cek ulang dengan `otonomassist status`

`status` menunjukkan workspace root tidak ada

- jalankan `otonomassist setup`
- perbaiki `OTONOMASSIST_WORKSPACE_ROOT`

Telegram tidak merespons

- cek `otonomassist status`
- pastikan token terpasang
- pastikan `TELEGRAM_OWNER_IDS` terisi
- bila DM policy `pairing`, user baru harus `/pair`

Agent terlalu agresif menulis file

- ubah workspace access ke `ro`
- audit kembali dengan `otonomassist status`

Output skill tidak sesuai format yang diminta

- gunakan `--view json|table|summary|short|markdown`
- atau minta eksplisit seperti `dalam bentuk tabel`

## Referensi

- [README.md](/d:/PROJECT/otonomAssist/README.md)
- [ARCHITECTURE.md](/d:/PROJECT/otonomAssist/ARCHITECTURE.md)
- [SKILL_FORMAT.md](/d:/PROJECT/otonomAssist/SKILL_FORMAT.md)
- [CHANGELOG.md](/d:/PROJECT/otonomAssist/CHANGELOG.md)
- [ROADMAP.md](/d:/PROJECT/otonomAssist/ROADMAP.md)
