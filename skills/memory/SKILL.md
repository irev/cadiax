# Memory

## Metadata
- name: memory
- description: Menyimpan, mencari, merangkum, dan mengambil memori kerja lokal untuk agent private AI
- aliases: [remember, mem, ingat]
- category: core
- autonomy_category: memory
- risk_level: medium
- side_effects: [memory_write, lessons_write]
- requires: []
- idempotency: mixed

## Description
Skill ini mengelola memori kerja lokal agent.

## Purpose
- Menyimpan fakta, keputusan, konteks, dan pelajaran operasional yang perlu dipakai ulang oleh agent.
- Menyediakan retrieval, ringkasan, dan konsolidasi memory tanpa mencampur fungsi planning atau eksekusi.

## Boundaries
- Gunakan skill ini untuk knowledge operasional pribadi agent, bukan untuk menjalankan task.
- Jangan gunakan untuk menyimpan secret mentah; gunakan capability `secrets` bila data bersifat sensitif.
- Jangan gunakan sebagai pengganti planner; task dan backlog tetap dikelola oleh `planner`.

## Primary Inputs
- `memory add <text>`
- `memory search <query>`
- `memory summarize`
- `memory consolidate`
- `memory journal <text>`
- `memory curate <text>`

## Expected Outputs
- Konfirmasi bahwa memory berhasil ditulis atau diubah.
- Hasil pencarian memory yang relevan beserta konteks ringkas.
- Ringkasan memory aktif atau hasil konsolidasi lesson yang siap dipakai ulang.
- Penolakan yang jelas bila operasi melanggar boundary session atau scope.

## State Touchpoints
- Durable memory state internal.
- Daily memory journal workspace.
- Curated memory workspace.
- Lesson dan summary cache yang diturunkan dari memory.

## Failure Modes
- Query terlalu umum sehingga hasil retrieval lemah.
- Penulisan curated memory ditolak karena session bukan `main`.
- Workspace tidak writable sehingga projection ke file harian gagal, walau durable store tetap berhasil.
- Input kosong atau argumen subcommand tidak valid.

## Success Criteria
- Memory dapat ditambah, dicari, diringkas, dan dikonsolidasikan tanpa merusak boundary scope/session.
- Retrieval mengembalikan hasil yang relevan, bukan sekadar daftar mentah.
- Durable store tetap menjadi source of truth walau projection workspace gagal.
- Operasi memory tidak menulis ke area secret atau planner secara tidak semestinya.

## Triggers
- memory
- remember
- mem
- ingat

## AI Instructions
Gunakan skill ini ketika user ingin:
- menyimpan fakta, keputusan, atau konteks penting
- mencari memori yang pernah disimpan
- melihat ringkasan memori kerja
- mengkonsolidasikan pelajaran ke knowledge markdown

Contoh:
- "ingat bahwa proyek ini fokus ke private ai" -> `memory add proyek ini fokus ke private ai`
- "cari memori tentang planner" -> `memory search planner`
- "ringkas memori aktif" -> `memory summarize`
- "konsolidasikan pelajaran terbaru" -> `memory consolidate`

## Execution
Handler Python terletak di `script/handler.py`
