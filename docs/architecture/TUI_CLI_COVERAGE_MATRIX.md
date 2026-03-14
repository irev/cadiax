# TUI CLI Coverage Matrix

Dokumen ini memetakan seberapa jauh `cadiax tui` sudah meng-cover surface CLI Cadiax.

Status yang dipakai:

- `covered`: sudah ada surface TUI yang nyata dan dapat dipakai
- `partial`: baru ada ringkasan, toggle, atau read-only snapshot
- `missing`: belum ada surface TUI yang relevan
- `out-of-scope`: sengaja tidak diposisikan sebagai target utama TUI saat ini

## Ringkasan

- `covered`: 6
- `partial`: 10
- `missing`: 12
- `out-of-scope`: 2

## Matriks

| CLI Surface | Status | TUI Coverage | Catatan |
|---|---|---|---|
| `setup` | covered | layar `Setup` | `cadiax setup` sekarang membuka TUI setup; wizard lama tetap ada via `--classic` |
| `doctor` | covered | layar `Doctor` | read-only diagnostic snapshot tersedia |
| `status` | covered | layar `Doctor` | alias konseptual untuk doctor |
| `paths` | covered | layar `Paths` | menampilkan `path_mode`, config, state, workspace, app, dashboard |
| `tui` | covered | shell utama | entrypoint operator utama |
| `dashboard` | partial | layar `Channels`, `Services`, `Setup` | ada toggle, host/access, port, admin API URL; belum parity penuh semua subcommand dashboard |
| `telegram` | partial | layar `Channels`, `Setup` | ada toggle, DM policy, require mention; belum parity penuh transport command |
| `service` | partial | layar `Services` | ada status ringkas dan `write service wrappers`; belum ada `run/show/write` parity penuh |
| `api` | partial | layar `Services` | baru status konseptual; belum ada action detail |
| `conversation-api` | partial | layar `Services` | baru status konseptual; belum ada action detail |
| `jobs` | missing | belum ada layar khusus | target berikutnya untuk queue/runtime operations |
| `worker` | missing | belum ada layar khusus | perlu action runtime dasar |
| `scheduler` | missing | belum ada layar khusus | perlu control dan status scheduling |
| `history` | missing | belum ada layar khusus | perlu surface observability |
| `events` | missing | belum ada layar khusus | perlu surface observability |
| `metrics` | missing | belum ada layar khusus | perlu surface observability |
| `heartbeat` | partial | terlihat lewat doctor/status | belum ada layar heartbeat khusus |
| `proactive` | partial | terlihat lewat doctor/status | belum ada layar proactive khusus |
| `privacy` | partial | terlihat lewat doctor/status | belum ada control/privacy view khusus |
| `notify` | missing | belum ada layar khusus | perlu action/operator notification surface |
| `email` | partial | layar `Channels` | baru snapshot status; belum ada global config form atau action |
| `whatsapp` | partial | layar `Channels` | baru snapshot status; belum ada global config form atau action |
| `agents` | partial | tercermin via setup/docs boundary | belum ada layar scope registry khusus |
| `startup` | missing | belum ada layar khusus | perlu startup document inspection |
| `bootstrap` | missing | belum ada layar khusus | perlu workspace bootstrap operator view |
| `external` | missing | belum ada layar khusus | perlu audit/approval surface |
| `skills` | missing | belum ada layar khusus | perlu taxonomy/audit surface |
| `config` | partial | terlipat ke `Setup`, `Doctor`, `Paths` | belum ada layar `config` eksplisit |
| `chat` | out-of-scope | tidak menjadi target utama TUI | CLI chat tetap lebih tepat untuk conversational flow |
| `run` | out-of-scope | tidak menjadi target utama TUI | command satu-shot tetap lebih tepat di CLI |

## Prioritas Gap

### Priority 1

Menutup gap operator/runtime yang paling penting setelah setup baseline:

- `jobs`
- `worker`
- `scheduler`
- `service`
- `metrics`
- `history`
- `events`

### Priority 2

Menutup governance dan channel/operator surface:

- `privacy`
- `notify`
- `agents`
- `startup`
- `bootstrap`

### Priority 3

Menutup audit/ekstensi yang lebih advanced:

- `external`
- `skills`
- `heartbeat`
- `proactive`
- parity lebih dalam untuk `email` dan `whatsapp`

## Boundary yang Sengaja Dipertahankan

- `email` dan `whatsapp` saat ini tetap `partial` karena runtime Cadiax masih memodelkan keduanya sebagai per-dispatch/API surface, bukan global credential configuration surface.
- `chat` dan `run` tidak dijadikan target parity TUI penuh karena lebih cocok tetap berada di CLI conversational/one-shot path.
- `cadiax setup --classic` tetap dipertahankan sebagai fallback prompt wizard, tetapi TUI adalah default setup surface.

## Acceptance Target Untuk Wave Berikutnya

Wave TUI berikutnya layak disebut `operator baseline complete` jika minimal:

- `jobs`, `worker`, `scheduler`, `metrics`, `history`, dan `events` punya layar TUI khusus
- `service` punya parity action dasar yang jelas
- `privacy` dan `startup` punya inspection surface
- `Channels` tidak lagi hanya snapshot, tetapi punya action operator yang relevan dan aman
