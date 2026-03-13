# Executor

## Metadata
- name: executor
- description: Menjalankan next task dari planner atau mengeksekusi command agent internal lalu menyimpan hasilnya ke memory dan planner
- aliases: [execute, run-task, act]
- category: core
- autonomy_category: execution
- risk_level: high
- side_effects: [planner_write, memory_write, lesson_write]
- requires: []
- idempotency: non_idempotent

## Description
Skill ini adalah jembatan dari planner ke eksekusi semi-otonom.

## Purpose
- Menjalankan task planner atau command internal secara terkontrol.
- Menutup loop antara planning, execution result, dan update memory/planner state.

## Boundaries
- Gunakan saat ada aksi yang memang perlu dieksekusi, bukan hanya dianalisis.
- Jangan gunakan untuk membuat tujuan baru tanpa planner.
- Aksi high-risk tetap tunduk pada policy, timeout, dan retry contract yang berlaku.

## Primary Inputs
- `executor next`
- `executor run <command>`
- `executor run planner next`
- `executor run memory add <text>`

## Expected Outputs
- Hasil eksekusi yang menyebut command yang dijalankan, status, dan error jika ada.
- Update planner task atau memory saat aksi memang berhasil atau gagal.
- Penolakan eksplisit untuk command yang tidak aman atau tidak valid.

## State Touchpoints
- Planner task state.
- Execution history dan audit trail.
- Memory/lesson write yang berasal dari outcome task.
- Runtime interaction context untuk scope/session inheritance.

## Failure Modes
- Task planner tidak tersedia.
- Command target gagal dieksekusi atau timeout.
- Retry policy habis sebelum hasil sukses tercapai.
- Policy memblokir aksi karena session/scope atau risk level.

## Success Criteria
- Task berikutnya dapat dijalankan tanpa kehilangan trace, timeout, atau retry metadata.
- Outcome eksekusi tercermin ke planner dan memory bila relevan.
- Eksekusi nested tetap mewarisi scope/session yang benar.
- Error bersifat operasional, jelas, dan tidak meninggalkan state separuh ter-update.

## Triggers
- executor
- execute
- run-task
- act

## AI Instructions
Gunakan skill ini ketika user ingin:
- menjalankan task berikutnya dari planner
- mengeksekusi task planner secara semi-otonom
- menindaklanjuti action yang sudah masuk backlog

Contoh:
- "jalankan task berikutnya" -> `executor next`
- "eksekusi memory add abc" -> `executor run memory add abc`

## Execution
Handler Python terletak di `script/handler.py`
