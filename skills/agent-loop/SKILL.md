# Agent Loop

## Metadata
- name: agent-loop
- description: Menjalankan loop semi-otonom dengan membaca profile, lessons, planner, dan memory untuk menentukan langkah berikutnya
- aliases: [loop, reflect, next-step]
- category: core
- autonomy_category: planning
- risk_level: medium
- side_effects: [memory_write]
- requires: [ai_provider]
- idempotency: non_idempotent

## Description
Skill ini menyatukan konteks persisten agent untuk refleksi dan langkah berikutnya.

## Purpose
- Membaca state agent dan menghasilkan refleksi, prioritas, atau next-step yang relevan.
- Menjadi capability reasoning operasional sebelum planning atau execution dilakukan.

## Boundaries
- Gunakan untuk refleksi terhadap kondisi agent, bukan untuk menjawab fakta real-world yang butuh verifikasi.
- Jangan gunakan sebagai pengganti executor; rekomendasi tindakan harus tetap diteruskan ke planner atau executor.
- Output reasoning harus menghormati policy, privacy, dan scope context aktif.

## Primary Inputs
- `agent-loop next`
- `agent-loop reflect`
- `agent-loop review`

## Expected Outputs
- Rekomendasi next-step yang bisa ditindaklanjuti.
- Refleksi ringkas tentang state planner, memory, lessons, atau backlog saat ini.
- Penjelasan bila AI provider tidak tersedia atau konteks tidak cukup.

## State Touchpoints
- Personality context.
- Planner state.
- Relevant memory dan lessons.
- Execution history yang memengaruhi refleksi.

## Failure Modes
- Provider AI tidak tersedia atau gagal merespons.
- Context terlalu tipis atau terlalu luas sehingga refleksi menjadi kabur.
- Scope/session membatasi memory yang dibutuhkan, sehingga rekomendasi kurang lengkap.
- Output reasoning ambigu dan tidak cukup operasional.

## Success Criteria
- Refleksi menghasilkan langkah berikutnya yang relevan dan bisa ditindaklanjuti.
- Skill tidak mengeksekusi aksi mutatif secara langsung.
- Hasil reasoning konsisten dengan scope, policy, dan privacy boundary.
- Failure dinyatakan jelas saat provider/context tidak memadai.

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
