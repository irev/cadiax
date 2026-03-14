# TUI Production Release Plan

Dokumen ini memetakan jalur publish/release ketika Cadiax TUI siap menjadi surface operator utama.

## Release Goal

Menjadikan TUI sebagai default operator/configuration surface tanpa mengganggu:

- CLI automation
- service runtime
- installer Windows/Linux
- dashboard optional frontend

## Release Waves

### Wave R1

Target:

- setup TUI default
- baseline setup edit/save
- services baseline
- observability baseline

### Wave R2

Target:

- runtime operations TUI
- startup/privacy/bootstrap surfaces
- agents/notify surface

### Wave R3

Target:

- external/skills/heartbeat/proactive
- channel parity lebih dalam
- interactive smoke pass lintas OS

## Publish Checklist

1. branch TUI up to date
2. TUI tests green
3. setup fallback `--classic` still works
4. Windows smoke test
5. Linux smoke test
6. docs sync:
   - README
   - INSTALL
   - TUI docs
7. release notes
8. PR summary

## Release Criteria

Sebuah release boleh mempromosikan Cadiax sebagai `TUI-first` jika:

- `cadiax setup` stabil sebagai default
- TUI punya parity operator untuk surface penting
- `doctor`, `paths`, `services`, `jobs`, `metrics`, `history`, `events`, `startup`, `privacy` tersedia
- Windows/Linux smoke test lulus
- residual risk tercatat jelas
