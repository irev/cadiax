# Decide

## Metadata
- name: decide
- description: Memilih aksi atau command terbaik berdasarkan state planner, runtime, dan sinyal operasional untuk AI otonom personal assistant
- aliases: [choose-action, decide-next, decision]
- category: capability
- autonomy_category: reasoning
- risk_level: low
- side_effects: [runtime_read]
- requires: []
- idempotency: idempotent
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk memilih next action atau memilih satu opsi terbaik dari beberapa opsi yang tersedia.

## Purpose
- Mengubah capability keputusan dari konsep implisit menjadi surface yang eksplisit.
- Menjembatani observasi state dengan aksi yang paling layak dilakukan berikutnya.

## Boundaries
- Gunakan untuk memilih tindakan terbaik dari state atau dari daftar opsi yang tersedia.
- Jangan gunakan untuk mengeksekusi aksi langsung; skill ini hanya memilih dan menjelaskan alasan.
- Skill ini read-only dan tidak menggantikan planner, executor, atau agent-loop.

## Primary Inputs
- `decide next`
- `decide between <opsi-a> | <opsi-b> [| <opsi-c>]`
- opsi tambahan:
  - `scope=<name>`
  - `roles=<a,b>`

## Expected Outputs
- Satu rekomendasi action atau command final.
- Alasan keputusan yang singkat dan dapat diaudit.
- Kandidat pendukung bila user memberi beberapa opsi.

## State Touchpoints
- Planner ready tasks.
- Runtime/config status snapshot.
- Scheduler and queue state.

## Failure Modes
- Tidak ada opsi yang cukup jelas untuk dibandingkan.
- Scope filter terlalu sempit sehingga planner terlihat kosong.
- State terlalu sepi sehingga keputusan jatuh ke fallback reasoning ringan.

## Success Criteria
- Skill memilih aksi yang konsisten dengan state runtime yang terlihat.
- Keputusan tidak mengeksekusi side effect.
- Scope/role filter tetap dihormati.

## Triggers
- decide
- choose-action
- decide-next
- decision

## AI Instructions
Gunakan skill ini ketika user ingin:
- menentukan langkah terbaik berikutnya
- memilih satu command dari beberapa opsi
- meminta keputusan operasional tanpa langsung mengeksekusi aksi

Contoh:
- "pilih next action terbaik" -> `decide next`
- "pilih antara monitor alerts atau executor next" -> `decide between monitor alerts | executor next`
- "tentukan aksi finance scope" -> `decide next scope=finance-agent roles=finance`

## Execution
Handler Python terletak di `script/handler.py`
