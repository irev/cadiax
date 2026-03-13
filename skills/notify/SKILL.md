# Notify

## Metadata
- name: notify
- description: Mengirim notifikasi durable ke channel internal, email, whatsapp, atau webhook untuk AI otonom personal assistant
- aliases: [alert, message-out, dispatch-notify]
- category: capability
- autonomy_category: delivery
- risk_level: medium
- side_effects: [notification_write, channel_dispatch]
- requires: []
- idempotency: non_idempotent
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk dispatch notifikasi keluar melalui notification dispatcher.

## Purpose
- Mengirim informasi keluar ke user, operator, atau channel target secara durable.
- Menjadi capability standar untuk outbound notification tanpa memaksa caller mengetahui detail dispatcher internal.

## Boundaries
- Gunakan untuk notifikasi operasional, alert, reminder, dan outbound delivery sederhana.
- Jangan gunakan untuk chat umum dua arah; gunakan `ai` atau interface conversation yang sesuai.
- Skill ini tunduk pada privacy, consent, quiet hours, dan scope policy yang sudah ada.
- Jangan gunakan untuk menyimpan secret atau mem-bypass policy channel.

## Primary Inputs
- `notify send <message>`
- `notify batch <message>`
- opsi tambahan:
  - `channel=<name>`
  - `title=<text>`
  - `target=<value>`
  - `delivery=<channel:target>` repeatable

## Expected Outputs
- Konfirmasi notifikasi tunggal atau batch yang dikirim.
- Status `queued` atau `deferred` bila privacy/policy menahan delivery.
- Error yang jelas bila input delivery tidak valid.

## State Touchpoints
- Durable notification state.
- Email/WhatsApp/webhook projection bila channel terkait dipakai.
- Event bus audit untuk notification dispatch.

## Failure Modes
- Input delivery batch tidak valid.
- Target wajib tidak diberikan untuk channel tertentu.
- Delivery ditunda karena quiet hours, consent, atau scope policy.
- Message kosong atau command tidak valid.

## Success Criteria
- Notification tercatat durable dan tertrace.
- Scope dan roles aktif diwariskan otomatis ke dispatch.
- Batch delivery dapat memproyeksikan multi-channel tanpa duplikasi notifikasi liar.
- Status `deferred` ditampilkan jelas saat delivery ditahan governance layer.

## Triggers
- notify
- alert
- message-out
- dispatch-notify

## AI Instructions
Gunakan skill ini ketika user ingin:
- mengirim alert ke operator
- mengirim notifikasi ke email, whatsapp, atau webhook
- membuat outbound reminder atau summary singkat

Contoh:
- "kirim notifikasi bahwa build selesai" -> `notify send build selesai`
- "alert operator lewat email" -> `notify send build gagal channel=email target=ops@example.com title=BuildAlert`
- "fanout ke beberapa channel" -> `notify batch deploy selesai delivery=email:ops@example.com delivery=whatsapp:+628123456789`

## Execution
Handler Python terletak di `script/handler.py`
