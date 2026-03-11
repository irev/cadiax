# OtonomAssist

Private AI CLI dengan fondasi otonom yang sekarang sudah mencakup:

- state persisten antar sesi
- personalisasi markdown
- memory dan lessons yang dibaca ulang otomatis
- planner, executor, dan runner untuk loop semi-otonom
- penyimpanan kredensial lokal yang terpisah dari konteks belajar

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

## Penyimpanan Data

State agent disimpan di:

```text
.otonomassist/
├── memory.jsonl
├── planner.json
├── profile.md
├── lessons.md
└── secrets.json
```

Makna file:

- `memory.jsonl`: memori mentah
- `planner.json`: task/goal
- `profile.md`: personalisasi agent
- `lessons.md`: pembelajaran yang dikonsolidasikan
- `secrets.json`: kredensial lokal

`.otonomassist/` sekarang di-ignore oleh git, jadi data lokal dan secret tidak ikut ter-commit.

Di Windows, value secret sekarang disimpan terenkripsi lokal memakai DPAPI sebelum ditulis ke `secrets.json`.

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

## Menjalankan Aplikasi

```bash
pip install -e .
otonomassist -i
```

Telegram runner:

```bash
otonomassist-telegram
```

Built-in commands:

```text
help
list
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

## Arsitektur

Lihat [ARCHITECTURE.md](/d:/PROJECT/otonomAssist/ARCHITECTURE.md) untuk alur detail runtime, storage, dan loop semi-otonom.

## Transport Ke Depan

Entry point pesan sekarang sudah dipisahkan lewat `Assistant.handle_message(...)`, sehingga CLI hanyalah salah satu transport. Ini sengaja disiapkan agar input ke depan bisa datang dari Telegram atau chat transport lain tanpa mengubah loop agent inti.
