# Identity

## Metadata
- name: identity
- description: Mengelola dan menginspeksi identity/session continuity lintas channel untuk AI otonom personal assistant
- aliases: [session, continuity, whoami]
- category: capability
- autonomy_category: continuity
- risk_level: medium
- side_effects: [identity_write, session_write]
- requires: []
- idempotency: mixed
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk melihat dan membentuk continuity identity/session lintas channel.

## Purpose
- Menginspeksi snapshot identity dan session yang sudah tersimpan.
- Membentuk atau memperbarui continuity record secara eksplisit saat dibutuhkan.

## Boundaries
- Gunakan untuk continuity identity, session, role, dan scope.
- Jangan gunakan untuk memory umum, profile persona, atau secrets.
- Operasi tulis terbatas pada pembentukan continuity record, bukan pengubahan bebas seluruh state identity.
- Skill ini tetap harus menghormati scope dan role visibility.

## Primary Inputs
- `identity show`
- `identity show scope=<name> roles=<a,b>`
- `identity resolve source=<name> user_id=<id> session_id=<id>`
- opsi tambahan untuk `resolve`:
  - `chat_id=<id>`
  - `identity_hint=<value>`
  - `scope=<name>`
  - `roles=<a,b>`

## Expected Outputs
- Snapshot identity/session yang terfilter sesuai scope.
- Konfirmasi resolve continuity yang menyebut `identity_id` dan `session_id`.
- Error yang jelas bila input resolve tidak cukup.

## State Touchpoints
- Durable identity state.
- Durable session state.
- Scope/role filtered continuity snapshot.

## Failure Modes
- Input resolve tidak punya principal yang cukup.
- Scope/role filter terlalu sempit sehingga snapshot kosong.
- Metadata resolve tidak valid atau tidak konsisten.

## Success Criteria
- Snapshot continuity bisa dilihat tanpa side effect yang tidak perlu.
- Resolve eksplisit membentuk identity/session yang stabil dan tertrace.
- Scope/role filter tetap dijaga pada mode show.
- Skill ini menjadi surface continuity eksplisit, bukan hanya implicit di conversation service atau admin API.

## Triggers
- identity
- session
- continuity
- whoami

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat continuity identity/session
- memeriksa identity yang aktif di suatu scope
- membentuk continuity record lintas channel secara eksplisit

Contoh:
- "lihat identity saat ini" -> `identity show`
- "cek continuity finance" -> `identity show scope=finance-agent roles=finance`
- "resolve identity untuk telegram user 200" -> `identity resolve source=telegram user_id=200 session_id=chat-200`

## Execution
Handler Python terletak di `script/handler.py`
