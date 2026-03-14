# TUI Validation and Test Plan

Dokumen ini mendefinisikan evaluasi dan pengujian untuk menjadikan Cadiax TUI layak produksi.

## Test Layers

### 1. Builder/Presenter Tests

Tujuan:

- memastikan setiap layar bisa dirender dengan snapshot yang valid
- menghindari regressi format/operator context

Contoh:

- `home`
- `paths`
- `doctor`
- `channels`
- `services`
- `worker`
- `scheduler`
- `jobs`
- `metrics`
- `history`
- `events`
- `startup`

### 2. Action Logic Tests

Tujuan:

- memastikan hotkey/action TUI mengubah state yang benar
- memastikan mutasi tidak menulis konfigurasi invalid

Contoh:

- toggle dashboard
- toggle Telegram
- save provider
- save workspace root/access
- save Telegram policy
- save dashboard host/port/admin API URL
- write service wrappers

### 3. CLI Dispatch Tests

Tujuan:

- memastikan `cadiax tui --screen ...` benar
- memastikan `cadiax setup` membuka TUI setup
- memastikan `cadiax setup --classic` tetap jalan

### 4. Runtime Snapshot Tests

Tujuan:

- memastikan TUI membaca source of truth runtime yang sama dengan CLI

Contoh:

- jobs summary
- scheduler summary
- metrics snapshot
- history snapshot
- event bus snapshot
- startup document snapshot

### 5. Interactive Smoke Tests

Tujuan:

- membuktikan aplikasi Textual benar-benar usable pada host nyata

Host minimum:

- Windows
- Linux / WSL

Checklist minimum:

1. buka `cadiax tui`
2. pindah layar dengan hotkey
3. buka `setup`
4. edit satu field
5. save perubahan
6. refresh
7. buka `services`
8. tulis wrapper
9. buka `doctor`
10. keluar tanpa crash

## Production Gates

### Gate A: Setup Safe

- `cadiax setup` membuka TUI
- save tidak menulis nilai kosong/invalid
- fallback `--classic` tetap aman

### Gate B: Runtime Safe

- read-only screens tidak crash saat data kosong
- write action tidak mengubah state yang salah
- command resolution tetap benar

### Gate C: Cross-Platform Safe

- TUI startup lulus di Windows
- TUI startup lulus di Linux/WSL
- layout path tetap konsisten

### Gate D: Release Safe

- test suite TUI lulus
- smoke test interaktif lulus
- docs sync
- release notes sync

## Known Residual Risk Until Full Production

- interactive Textual host behavior belum seluas test builder/action
- belum semua CLI surface punya parity TUI
- channel model `email/whatsapp` masih partial karena runtime credential model belum global
