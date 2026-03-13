# Secrets

## Metadata
- name: secrets
- description: Menyimpan, menampilkan metadata, memperbarui, dan menghapus kredensial lokal untuk private AI tanpa memasukkannya ke memory atau prompt AI
- aliases: [credential, creds, secret]
- category: governance
- autonomy_category: governance
- risk_level: critical
- side_effects: [secret_write]
- requires: [secure_storage]
- idempotency: non_idempotent

## Description
Skill ini mengelola penyimpanan kredensial lokal.

## Purpose
- Menyimpan dan mengelola credential lokal secara aman tanpa memasukkannya ke memory umum atau prompt AI.
- Menjadi satu-satunya capability standar untuk operasi secret dan credential lifecycle.

## Boundaries
- Gunakan untuk secret, token, API key, dan credential metadata.
- Jangan gunakan `memory`, `profile`, atau `workspace` untuk menyimpan nilai secret mentah.
- Tampilkan metadata bila dibutuhkan, tetapi jangan membocorkan nilai secret ke output biasa.
- Operasi ini bersifat high-risk dan harus tetap tunduk pada policy serta secure storage availability.

## Primary Inputs
- `secrets set <name> <value>`
- `secrets list`
- `secrets show <name>`
- `secrets delete <name>`
- `secrets import-env`

## Expected Outputs
- Konfirmasi bahwa secret berhasil disimpan, diperbarui, atau dihapus.
- Daftar nama secret atau metadata aman tanpa membocorkan nilai sensitif.
- Penolakan yang jelas bila storage aman tidak tersedia atau operasi tidak valid.

## State Touchpoints
- Secure local secret storage.
- Secret metadata audit trail.
- Tidak boleh menulis nilai secret ke memory umum, planner, atau prompt context.

## Failure Modes
- Secure storage tidak tersedia atau gagal dibuka.
- Nama secret tidak valid atau duplikat dalam konteks operasi tertentu.
- User mencoba melihat nilai secret secara mentah di jalur yang tidak diizinkan.
- Import environment gagal karena source tidak tersedia atau mapping tidak valid.

## Success Criteria
- Nilai secret tidak pernah bocor ke memory, prompt, atau output audit biasa.
- User tetap bisa melihat metadata yang cukup untuk operasi administratif.
- Create/update/delete secret konsisten dan tertrace.
- Failure dinyatakan jelas tanpa menampilkan data sensitif.

## Triggers
- secrets
- credential
- creds
- secret

## AI Instructions
Gunakan skill ini ketika user ingin:
- menyimpan API key atau token lokal
- melihat nama kredensial yang tersimpan
- menghapus kredensial
- melihat metadata kredensial tanpa membocorkan nilainya
- mengimpor credential dari environment ke encrypted local secrets

Contoh:
- "simpan token github" -> `secrets set github_token <nilai>`
- "lihat daftar secret" -> `secrets list`
- "hapus secret lama" -> `secrets delete github_token`
- "import credential dari .env" -> `secrets import-env`

## Execution
Handler Python terletak di `script/handler.py`
