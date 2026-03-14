# TUI CLI Coverage Matrix

Dokumen ini memetakan seberapa jauh `cadiax tui` sudah meng-cover surface CLI Cadiax.

Status yang dipakai:

- `covered`: sudah ada surface TUI yang nyata dan dapat dipakai
- `partial`: baru ada ringkasan, toggle, atau read-only snapshot
- `missing`: belum ada surface TUI yang relevan
- `out-of-scope`: sengaja tidak diposisikan sebagai target utama TUI saat ini

## Ringkasan

- `covered`: 16
- `partial`: 7
- `missing`: 5
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
| `jobs` | covered | layar `Jobs` | queue/runtime inspection sudah ada |
| `worker` | covered | layar `Worker` | status worker dan action one-shot aman sudah ada |
| `scheduler` | covered | layar `Scheduler` | status scheduler dan action one-shot aman sudah ada |
| `history` | covered | layar `History` | recent execution history inspection sudah ada |
| `events` | covered | layar `Events` | internal event bus inspection sudah ada |
| `metrics` | covered | layar `Metrics` | execution metrics inspection sudah ada |
| `heartbeat` | partial | terlihat lewat doctor/status | belum ada layar heartbeat khusus |
| `proactive` | partial | terlihat lewat doctor/status | belum ada layar proactive khusus |
| `privacy` | covered | layar `Privacy` | redaction, quiet hours, retention, scoped controls sudah bisa diinspeksi |
| `notify` | covered | layar `Notify` | snapshot history, by-channel, by-scope, latest notification sudah ada |
| `email` | partial | layar `Channels` | baru snapshot status; belum ada global config form atau action |
| `whatsapp` | partial | layar `Channels` | baru snapshot status; belum ada global config form atau action |
| `agents` | covered | layar `Agents` | scope registry inspection dari `AGENTS.md` sudah ada |
| `startup` | covered | layar `Startup` | startup document inspection sudah ada |
| `bootstrap` | covered | layar `Bootstrap` | workspace bootstrap inspection dan action seed runtime docs sudah ada |
| `external` | missing | belum ada layar khusus | perlu audit/approval surface |
| `skills` | missing | belum ada layar khusus | perlu taxonomy/audit surface |
| `config` | partial | terlipat ke `Setup`, `Doctor`, `Paths` | belum ada layar `config` eksplisit |
| `chat` | out-of-scope | tidak menjadi target utama TUI | CLI chat tetap lebih tepat untuk conversational flow |
| `run` | out-of-scope | tidak menjadi target utama TUI | command satu-shot tetap lebih tepat di CLI |

## Prioritas Gap

### Priority 1

Menutup action/operator parity yang masih paling penting setelah inspection baseline:

- `service`
- `notify`
- `agents`

### Priority 2

Menutup audit/ekstensi yang lebih advanced:

- `external`
- `skills`
- `heartbeat`
- `proactive`
- parity lebih dalam untuk `email` dan `whatsapp`

### Priority 3

Merapikan mutasi aman dan host smoke:

- action privacy yang aman
- action bootstrap optional templates
- interactive smoke test Windows/Linux

## Boundary yang Sengaja Dipertahankan

- `email` dan `whatsapp` saat ini tetap `partial` karena runtime Cadiax masih memodelkan keduanya sebagai per-dispatch/API surface, bukan global credential configuration surface.
- `chat` dan `run` tidak dijadikan target parity TUI penuh karena lebih cocok tetap berada di CLI conversational/one-shot path.
- `cadiax setup --classic` tetap dipertahankan sebagai fallback prompt wizard, tetapi TUI adalah default setup surface.

## Acceptance Target Untuk Wave Berikutnya

Wave TUI berikutnya layak disebut `operator baseline complete` jika minimal:

- `service` punya parity action dasar yang jelas
- `worker` dan `scheduler` punya action operator yang aman
- `privacy`, `startup`, dan `bootstrap` sudah punya inspection surface
- `notify` dan `agents` sudah punya layar khusus
- `Channels` tidak lagi hanya snapshot, tetapi punya action operator yang relevan dan aman
