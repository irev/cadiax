# Research

## Metadata
- name: research
- description: Memverifikasi informasi faktual, tanggal, jadwal, dan klaim real-world dengan web lookup sebelum menjawab
- aliases: [search-web, verify, browse]
- category: capability
- autonomy_category: knowledge
- risk_level: medium
- side_effects: [network_access]
- requires: [ai_provider, web_search]
- idempotency: best_effort

## Description
Skill ini dipakai untuk pertanyaan yang butuh validasi fakta dunia nyata, terutama jika sensitif terhadap tanggal, jadwal, atau informasi terbaru.

Alur jawabnya:

1. cek tanggal saat ini sebagai anchor temporal
2. lakukan pencarian sesuai konteks user
3. rangkum hasil dalam bentuk data terstruktur
4. tampilkan status verifikasi, confidence, data penting, gap, dan sumber

## Purpose
- Memverifikasi informasi real-world yang bisa berubah terhadap waktu.
- Menghasilkan jawaban berbasis sumber dengan status verifikasi yang eksplisit.

## Boundaries
- Gunakan hanya saat freshness, fakta publik, atau source attribution penting.
- Jangan gunakan untuk inspeksi workspace lokal atau memory internal.
- Bila provider/web search tidak tersedia, skill tetap harus jujur menyatakan keterbatasan verifikasi.

## Primary Inputs
- `research <query>`
- Query sebaiknya menyebut entitas, lokasi, dan horizon waktu yang dicari.

## Expected Outputs
- Ringkasan jawaban yang menyebut status verifikasi dan confidence.
- Data points penting yang relevan dengan pertanyaan user.
- Daftar source atau gap jika verifikasi tidak penuh.
- Format terstruktur yang konsisten untuk reasoning atau follow-up.

## State Touchpoints
- Network/web search capability.
- AI provider response metadata bila tersedia.
- Audit trail untuk query yang diverifikasi.

## Failure Modes
- Web search tidak tersedia atau provider gagal.
- Query terlalu luas, ambigu, atau tidak punya anchor waktu.
- Sumber yang ditemukan saling bertentangan.
- Informasi tidak cukup baru untuk menjawab dengan yakin.

## Success Criteria
- Jawaban menyatakan apa yang terverifikasi, dari mana, dan apa gap yang tersisa.
- Informasi sensitif terhadap waktu selalu di-anchorkan ke tanggal yang jelas.
- Output tidak mengarang sumber saat verifikasi tidak tersedia.
- Hasil cukup terstruktur untuk dipakai sebagai input capability lain.

## Triggers
- research
- search-web
- verify
- browse
- cari informasi
- cek informasi
- cari fakta
- verifikasi

## AI Instructions
Gunakan skill ini ketika user meminta informasi yang perlu divalidasi dari internet atau sumber real-world, misalnya:
- tanggal hari raya
- jadwal/libur
- informasi terbaru
- fakta yang bisa berubah dari waktu ke waktu

Saat mengeksekusi:
- mulai dari tanggal saat ini
- cari sumber yang paling relevan dengan konteks user
- keluarkan hasil dalam bentuk data JSON yang ringkas dan jelas
- isi field penting seperti `answer`, `summary`, `data_points`, `notes`, `gaps`, dan `sources`
- jika provider tidak punya web search, tetap hasilkan JSON tetapi tandai status verifikasi dengan jelas

Contoh:
- "kapan idul fitri 2026?" -> `research kapan idul fitri 2026 di indonesia`
- "buat rencana libur idul fitri 2026" -> `research buat rencana libur idul fitri 2026`
- "siapa presiden saat ini" -> `research siapa presiden saat ini`

## Execution
Handler Python terletak di `script/handler.py`
