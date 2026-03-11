# Planner

## Metadata
- name: planner
- description: Mengelola tujuan, backlog, langkah berikutnya, dan status task untuk agent private AI yang bekerja mandiri
- aliases: [plan, task, backlog]
- category: core

## Description
Skill ini mengelola state perencanaan agent.

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
