# Planner

## Metadata
- name: planner
- description: Mengelola tujuan, backlog, langkah berikutnya, dan status task untuk agent private AI yang bekerja mandiri
- aliases: [plan, task, backlog]
- category: core
- autonomy_category: planning
- risk_level: medium
- side_effects: [planner_state]
- requires: []
- idempotency: non_idempotent

## Description
Skill ini mengelola state perencanaan agent.

## Purpose
- Mengelola tujuan, backlog, prioritas, dan next action untuk pekerjaan agent.
- Menjadi source of truth untuk status task yang akan ditindaklanjuti oleh automation atau executor.

## Boundaries
- Gunakan untuk task agent yang perlu dilacak statusnya.
- Jangan gunakan untuk tanya-jawab umum atau rencana non-operasional; gunakan `ai` atau `research` sesuai konteks.
- Skill ini tidak menjalankan task; eksekusi tetap dilakukan oleh `executor`, `worker`, atau runtime automation.

## Primary Inputs
- `planner set-goal <goal>`
- `planner add <task>`
- `planner next`
- `planner done <id>`
- `planner block <id> <reason>`
- `planner note <id> <note>`

## Expected Outputs
- Snapshot backlog atau next task yang jelas.
- Konfirmasi perubahan status task.
- Penjelasan bila task tidak ditemukan atau transisi status tidak valid.
- Task metadata yang cukup untuk diteruskan ke executor.

## State Touchpoints
- Durable planner task state.
- Planner notes dan task status history.
- Scope/session metadata untuk follow-up automation.

## Failure Modes
- Task ID tidak ditemukan.
- Status transition tidak valid untuk state task saat ini.
- Goal atau task baru terlalu ambigu sehingga sulit dieksekusi.
- Scope aktif tidak punya visibility terhadap task yang diminta.

## Success Criteria
- Setiap task yang dibuat dapat dilacak statusnya dengan jelas.
- `planner next` selalu mengembalikan kandidat tindakan yang konsisten dengan scope aktif.
- Update status dan note tidak bocor ke scope lain.
- Planner tetap stabil walau backlog kosong atau task tidak valid.

## Triggers
- planner
- plan
- task
- backlog

## AI Instructions
Gunakan skill ini ketika user ingin:
- memecah tujuan menjadi task
- menambahkan task baru
- melihat langkah berikutnya
- menandai task selesai atau terblokir
- mengelola backlog kerja agent internal

Jangan gunakan skill ini untuk rencana umum non-agent seperti:
- itinerary liburan
- jadwal perjalanan
- outline acara umum

Untuk rencana umum seperti itu, gunakan skill `ai`.

Contoh:
- "buat rencana kerja untuk memory system" -> `planner set-goal memory system`
- "tambahkan task buat skill workspace" -> `planner add buat skill workspace`
- "apa langkah berikutnya" -> `planner next`
- "task 2 selesai" -> `planner done 2`
- "buat rencana libur idul fitri 2026" -> gunakan `ai`, bukan `planner`

## Execution
Handler Python terletak di `script/handler.py`
