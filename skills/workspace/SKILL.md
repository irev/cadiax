# Workspace

## Metadata
- name: workspace
- description: Menjelajah, membaca, mencari, dan merangkum isi workspace proyek lokal untuk agent private AI
- aliases: [files, repo, project]
- category: capability

## Description
Skill ini memberi kemampuan inspeksi workspace lokal.

## Triggers
- workspace
- files
- repo
- project

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat struktur file proyek
- membaca file tertentu
- mencari teks di workspace
- merangkum isi direktori

Contoh:
- "baca file assistant.py" -> `workspace read src/otonomassist/core/assistant.py`
- "cari string OPENAI_MODEL" -> `workspace find OPENAI_MODEL`
- "lihat struktur src" -> `workspace tree src`
- "lihat struktur file yang ada di workspace" -> `workspace tree .`
- "baca README.md" -> `workspace read README.md`

## Execution
Handler Python terletak di `script/handler.py`
