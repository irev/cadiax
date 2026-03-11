# Research

## Metadata
- name: research
- description: Memverifikasi informasi faktual, tanggal, jadwal, dan klaim real-world dengan web lookup sebelum menjawab
- aliases: [search-web, verify, browse]
- category: capability

## Description
Skill ini dipakai untuk pertanyaan yang butuh validasi fakta dunia nyata, terutama jika sensitif terhadap tanggal, jadwal, atau informasi terbaru.

Alur jawabnya:

1. cek tanggal saat ini sebagai anchor temporal
2. lakukan pencarian sesuai konteks user
3. rangkum hasil dalam bentuk data terstruktur
4. tampilkan status verifikasi, confidence, data penting, gap, dan sumber

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
