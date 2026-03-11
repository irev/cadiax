# Worker

## Metadata
- name: worker
- description: Memproses runtime job queue berbasis planner secara eksplisit untuk loop otonom yang lebih terstruktur
- aliases: [job-worker, queue-worker]
- category: core
- autonomy_category: execution
- risk_level: high
- side_effects: [job_queue_write, planner_write, memory_write, lesson_write]
- requires: []
- idempotency: non_idempotent

## Description
Skill ini memproses runtime job queue sebagai lapisan di antara planner dan executor.

## Triggers
- worker
- job-worker
- queue-worker

## AI Instructions
Gunakan skill ini ketika user ingin memproses job queue runtime secara eksplisit, bukan langsung menjalankan runner biasa.

Contoh:
- "proses satu job" -> `worker once`
- "enqueue lalu proses job" -> `worker once --enqueue`

## Execution
Handler Python terletak di `script/handler.py`
