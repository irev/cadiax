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
