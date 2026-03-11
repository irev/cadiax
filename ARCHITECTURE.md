# Arsitektur OtonomAssist

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

## Diagram Sistem

```text
┌──────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                               │
│                     src/otonomassist/cli.py                          │
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
│                          Assistant Layer                             │
│                 src/otonomassist/core/assistant.py                   │
│  - load .env                                                         │
│  - fallback ke local secrets untuk credential runtime                │
│  - ensure .otonomassist storage                                      │
│  - load skills                                                       │
│  - inject persistent context into prompts                            │
│  - pilih view presentasi hasil                                       │
│  - format structured result untuk user                               │
└───────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────────┐   ┌───────────────────────────────────┐
│        Skill Runtime         │   │         AI Provider Layer         │
│  registry + loader           │   │         OpenAI, etc.              │
└───────────────┬──────────────┘   └───────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Result Builder + Formatter                        │
│  src/otonomassist/core/result_builder.py                             │
│  src/otonomassist/core/result_formatter.py                           │
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
│  .otonomassist/profile.md                                            │
│  .otonomassist/lessons.md                                            │
│  .otonomassist/planner.json                                          │
│  .otonomassist/memory.jsonl                                          │
│  .otonomassist/secrets.json                                          │
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

- [result_builder.py](/d:/PROJECT/otonomAssist/src/otonomassist/core/result_builder.py)
- [result_formatter.py](/d:/PROJECT/otonomAssist/src/otonomassist/core/result_formatter.py)
- [assistant.py](/d:/PROJECT/otonomAssist/src/otonomassist/core/assistant.py)

## Persistent Context

Modul [agent_context.py](/d:/PROJECT/otonomAssist/src/otonomassist/core/agent_context.py) adalah inti persistence.

Ia menangani:

- bootstrap file
- profile markdown
- lessons markdown
- planner json
- memory jsonl
- secrets json
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

- root workspace berasal dari `OTONOMASSIST_WORKSPACE_ROOT` atau default ke root project
- path absolut dan relatif di-resolve lalu divalidasi agar tetap berada di bawah workspace root
- traversal ke luar workspace ditolak
- symlink yang mengarah ke luar workspace diabaikan saat enumerasi
- mode akses kebijakan disiapkan lewat `OTONOMASSIST_WORKSPACE_ACCESS`, default `ro`

Ini penting agar inspeksi file oleh AI tetap terbatas pada workspace lokal yang diizinkan.

## Penyimpanan Kredensial

Kredensial user sebaiknya disimpan di:

```text
.otonomassist/secrets.json
```

dan dikelola lewat skill `secrets`.

Prinsipnya:

- simpan secret terpisah dari memory/lessons/profile
- runtime membaca env lebih dulu, lalu fallback ke `secrets`
- jangan injeksikan secret ke prompt AI secara default
- tampilkan hanya fingerprint, bukan value
- ignore file ini dari git

Ini penting karena `memory`, `lessons`, dan `profile` memang dibaca ulang untuk pembelajaran; secret tidak boleh ikut tercampur di sana.

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

State authorization Telegram disimpan terpisah di:

```text
.otonomassist/telegram_auth.json
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

- background daemon sungguhan di luar command manual
- Telegram masih long polling, belum webhook
- tool execution policy yang lebih granular
- retrieval memory semantik
- web-grounded research saat ini paling kuat pada provider OpenAI

## Langkah Berikut yang Logis

- adapter Telegram yang memanggil `Assistant.handle_message(...)`
- policy user/chat authorization yang lebih granular untuk Telegram
- scheduler/background worker
- retrieval memory berbasis embedding atau ranking
- executor policy yang lebih ketat untuk aksi tulis/ubah file
