# TUI Full Migration Plan

Dokumen ini mendefinisikan target akhir bahwa seluruh interaksi operator/user administratif Cadiax dilakukan melalui antarmuka TUI, sementara CLI tekstual tetap dipertahankan terutama sebagai:

- bootstrap entrypoint
- compatibility surface
- automation/script surface
- fallback path untuk recovery

## Target Akhir

Cadiax harus memiliki model interaksi berikut:

1. `cadiax`
   - menjalankan assistant/chat runtime seperti sekarang
2. `cadiax setup`
   - membuka TUI setup sebagai default
3. `cadiax tui`
   - membuka TUI operator penuh
4. CLI command tree lain
   - tetap ada untuk scripting, recovery, CI, dan automation
   - tetapi seluruh capability operator utamanya harus punya parity di TUI

## Prinsip Desain

- TUI adalah `primary operator UX`
- CLI adalah `automation and recovery UX`
- Web dashboard tetap `optional frontend observability`
- tidak boleh ada konfigurasi penting yang hanya bisa diubah dari dashboard web
- setiap mutasi TUI harus memakai service/helper runtime yang sama dengan CLI

## Domain yang Harus Ditutup

### 1. Setup and Configuration

Harus 100% tersedia di TUI:

- provider
- model/base URL
- workspace root
- workspace access
- Telegram global settings
- dashboard settings
- command/path diagnostics

### 2. Runtime Operations

Harus tersedia di TUI:

- jobs
- worker
- scheduler
- service targets
- admin API / conversation API basic operations

### 3. Observability

Harus tersedia di TUI:

- doctor
- status
- paths
- metrics
- history
- events
- startup documents
- heartbeat
- proactive snapshot

### 4. Governance

Harus tersedia di TUI:

- privacy controls
- bootstrap state
- agent scopes
- notification surface
- external approval/audit
- skill taxonomy/audit

### 5. Channels

Harus tersedia di TUI:

- Telegram
- dashboard
- email snapshot
- WhatsApp snapshot

Catatan:
- email/WhatsApp global credential setup baru bisa dibuat jika runtime memang memutuskan model credential global resmi

## CLI to TUI Strategy

### Tetap Dipertahankan di CLI

- `chat`
- `run`
- scripting-oriented JSON output
- install/reinstall/uninstall shell entrypoints

### Dipindahkan Menjadi TUI-First

- `setup`
- `doctor` inspection flow
- `paths` operator interpretation
- service inspection
- jobs/worker/scheduler operator flows
- privacy/operator governance inspection

### Tetap Ada Sebagai Fallback

- `setup --classic`
- command recovery read-only
- CI-friendly command output

## Migration Phases

### Phase M1: Setup and Core Control

Status:

- selesai sebagian besar

Includes:

- TUI shell
- setup default
- doctor
- paths
- channels baseline
- services baseline

### Phase M2: Runtime Operations and Observability

Target:

- jobs
- worker
- scheduler
- metrics
- history
- events
- service target detail

### Phase M3: Governance and Workspace Control

Target:

- privacy
- startup
- bootstrap
- agents
- notify

### Phase M4: Extended Surfaces

Target:

- external
- skills
- heartbeat
- proactive
- deeper email/whatsapp parity

### Phase M5: TUI-First Production Hardening

Target:

- interactive TUI smoke coverage
- host-level validation Windows/Linux
- error states and recovery actions
- accessibility/readability pass
- documentation and release hardening

## Exit Criteria

Cadiax dapat dianggap `TUI-first production ready` jika:

- semua surface operator penting punya parity TUI
- setup/reconfigure tidak lagi memerlukan wizard prompt lama untuk penggunaan normal
- service/runtime observability cukup dilakukan dari TUI
- privacy and governance inspection cukup dilakukan dari TUI
- smoke test interaktif Windows dan Linux lulus
- CLI fallback tetap aman untuk automation
