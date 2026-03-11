# Executor

## Metadata
- name: executor
- description: Menjalankan next task dari planner atau mengeksekusi command agent internal lalu menyimpan hasilnya ke memory dan planner
- aliases: [execute, run-task, act]
- category: core

## Description
Skill ini adalah jembatan dari planner ke eksekusi semi-otonom.

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
