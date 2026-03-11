# Help

## Metadata
- name: help
- description: Menampilkan daftar semua skill yang tersedia
- aliases: [?, bantuan]
- category: system

## Description
Skill ini menampilkan daftar semua skill yang tersedia dan cara menggunakan asisten.

## Triggers
- "help"
- "?"

## AI Instructions
Ketika user meminta bantuan atau ingin melihat daftar skill, arahkan ke skill ini.

Contoh:
- "help" → Tampilkan daftar skill
- "bantuan" → Tampilkan daftar skill
- "apa yang bisa kamu lakukan" → Tampilkan daftar skill

## Notes
Handler untuk skill ini ditangani langsung oleh assistant (menggunakan method `get_help()`).
