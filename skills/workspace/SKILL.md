# Workspace

## Metadata
- name: workspace
- description: Menjelajah, membaca, mencari, dan merangkum isi workspace proyek lokal untuk agent private AI
- aliases: [inspect, files, repo, project]
- category: capability
- autonomy_category: environment
- risk_level: medium
- side_effects: [workspace_read]
- requires: [workspace_access]
- idempotency: idempotent

## Description
Skill ini memberi kemampuan inspeksi workspace lokal.

## Purpose
- Menginspeksi struktur, isi, dan sinyal penting dari workspace lokal secara aman.
- Menjadi capability utama untuk membaca project state sebelum reasoning, planning, atau editing dilakukan.

## Boundaries
- Gunakan untuk membaca, mencari, dan merangkum workspace lokal.
- Jangan gunakan untuk memory management atau planning task internal.
- Jangan mengandalkan skill ini untuk fakta eksternal; gunakan `research` bila butuh verifikasi internet.

## Primary Inputs
- `workspace tree <path>`
- `workspace read <path>`
- `workspace find <pattern>`
- `workspace summary <path>`

## Expected Outputs
- Struktur file atau isi file yang akurat.
- Hasil pencarian teks beserta lokasi yang relevan.
- Ringkasan direktori atau file yang cukup untuk reasoning lanjutan.
- Error yang jelas bila path tidak ditemukan atau tidak dapat diakses.

## State Touchpoints
- File dan direktori workspace lokal.
- Tidak boleh menulis state operasional kecuali audit umum runtime.

## Failure Modes
- Path tidak ada atau di luar workspace yang diizinkan.
- File terlalu besar atau biner sehingga tidak cocok untuk dibaca langsung.
- Pattern search terlalu umum sehingga hasil terlalu banyak.
- Permission lokal tidak mengizinkan akses file tertentu.

## Success Criteria
- Struktur dan isi workspace yang dibaca sesuai kondisi lokal saat ini.
- Hasil cukup akurat untuk dipakai oleh skill lain tanpa asumsi berlebihan.
- Tidak ada side effect tulis pada workspace saat operasi read-only dijalankan.
- Error akses dan path invalid dilaporkan dengan jelas.

## Triggers
- workspace
- inspect
- files
- repo
- project

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat struktur file proyek
- membaca file tertentu
- mencari teks di workspace
- merangkum isi direktori

Contoh:
- "baca file assistant.py" -> `workspace read src/otonomassist/core/assistant.py`
- "cari string OPENAI_MODEL" -> `workspace find OPENAI_MODEL`
- "lihat struktur src" -> `workspace tree src`
- "lihat struktur file yang ada di workspace" -> `workspace tree .`
- "baca README.md" -> `workspace read README.md`

## Execution
Handler Python terletak di `script/handler.py`
