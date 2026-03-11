# Agent Loop

## Metadata
- name: agent-loop
- description: Menjalankan loop semi-otonom dengan membaca profile, lessons, planner, dan memory untuk menentukan langkah berikutnya
- aliases: [loop, reflect, next-step]
- category: core

## Description
Skill ini menyatukan konteks persisten agent untuk refleksi dan langkah berikutnya.

## Triggers
- agent-loop
- loop
- reflect
- next-step

## AI Instructions
Gunakan skill ini ketika user ingin:
- meminta langkah berikutnya secara mandiri
- meminta refleksi dari state agent saat ini
- meminta rekomendasi prioritas berdasarkan planner dan lessons

Contoh:
- "apa langkah berikutnya" -> `agent-loop next`
- "refleksikan kondisi agent saat ini" -> `agent-loop reflect`

## Execution
Handler Python terletak di `script/handler.py`
