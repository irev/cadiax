# TUI CLI Coverage Matrix

Dokumen ini memetakan seberapa jauh `cadiax tui` sudah meng-cover surface CLI Cadiax.

Status yang dipakai:

- `covered`: sudah ada surface TUI yang nyata dan dapat dipakai
- `partial`: baru ada ringkasan, toggle, atau read-only snapshot
- `missing`: belum ada surface TUI yang relevan
- `out-of-scope`: sengaja tidak diposisikan sebagai target utama TUI saat ini

## Ringkasan

- `covered`: 20
- `partial`: 5
- `missing`: 3
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
| `service` | partial | layar `Services` | ada target selection, wrapper write, dan probe health; belum ada `run/show/write` parity penuh |
| `api` | partial | layar `Services` | ada probe `admin-api /health`; belum ada action detail lain |
| `conversation-api` | partial | layar `Services` | ada probe `/health`; belum ada action detail lain |
| `jobs` | covered | layar `Jobs` | queue/runtime inspection sudah ada |
| `worker` | covered | layar `Worker` | status worker dan action one-shot aman sudah ada |
| `scheduler` | covered | layar `Scheduler` | status scheduler dan action one-shot aman sudah ada |
| `history` | covered | layar `History` | recent execution history inspection sudah ada |
| `events` | covered | layar `Events` | internal event bus inspection sudah ada |
| `metrics` | covered | layar `Metrics` | execution metrics inspection sudah ada |
| `heartbeat` | covered | layar `Heartbeat` | heartbeat state, pulse summary, dan guide preview sudah ada |
| `proactive` | covered | layar `Proactive` | insight snapshot dan governance ringkas sudah ada |
| `privacy` | covered | layar `Privacy` | redaction, quiet hours, retention, scoped controls sudah bisa diinspeksi |
| `notify` | covered | layar `Notify` | snapshot history, by-channel, by-scope, latest notification sudah ada |
| `email` | partial | layar `Channels` | ada snapshot status dan test dispatch ke target terakhir; belum ada global config form |
| `whatsapp` | partial | layar `Channels` | ada snapshot status dan test dispatch ke target terakhir; belum ada global config form |
| `agents` | covered | layar `Agents` | scope registry inspection dari `AGENTS.md` sudah ada |
| `startup` | covered | layar `Startup` | startup document inspection sudah ada |
| `bootstrap` | covered | layar `Bootstrap` | workspace bootstrap inspection dan action seed runtime docs sudah ada |
| `external` | covered | layar `External` | external asset audit, trust policy, approval state, dan layout sudah ada |
| `skills` | covered | layar `Skills` | taxonomy/audit snapshot dari skill registry sudah ada |
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
- `privacy`, `startup`, `bootstrap`, `heartbeat`, dan `proactive` sudah punya inspection surface
- `notify` dan `agents` sudah punya layar khusus
- `Channels` tidak lagi hanya snapshot, tetapi punya action operator yang relevan dan aman
