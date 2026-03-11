# Runner

## Metadata
- name: runner
- description: Menjalankan loop otomatis berbasis planner, executor, dan agent-loop untuk beberapa langkah atau sampai idle
- aliases: [run-loop, daemon, autopilot]
- category: core

## Description
Skill ini menjalankan loop eksekusi semi-otonom.

## Triggers
- runner
- run-loop
- daemon
- autopilot

## AI Instructions
Gunakan skill ini ketika user ingin:
- menjalankan planner beberapa langkah berturut-turut
- menjalankan loop sampai tidak ada task todo
- meminta autopilot singkat untuk agent

Contoh:
- "jalankan loop 3 langkah" -> `runner steps 3`
- "jalan sampai idle" -> `runner until-idle`
- "autopilot sekali" -> `runner once`

## Execution
Handler Python terletak di `script/handler.py`
