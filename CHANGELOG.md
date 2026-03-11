# Changelog

Dokumen ini merangkum perubahan penting yang sudah mendarat di OtonomAssist.

## Unreleased

### Added

- setup wizard interaktif untuk first-run dan reconfigure
- audit konfigurasi read-only lewat `status`, `doctor`, dan `config status`
- level status konfigurasi `healthy`, `warning`, `critical`
- roadmap implementasi 3 fase:
  - `Phase 1: Semi-Production Hardening`
  - `Phase 2: Autonomous Runtime`
  - `Phase 3: Production Agent Platform`
- execution history terstruktur dengan `trace_id` untuk command dan skill
- command `otonomassist history` untuk melihat jejak eksekusi terbaru
- timeout skill global melalui `OTONOMASSIST_SKILL_TIMEOUT_SECONDS`
- klasifikasi status eksekusi dasar: `ok`, `blocked`, `error`, `timeout`, `degraded`
- `doctor/status --json` untuk audit machine-readable
- retry dasar di `executor` untuk kegagalan transient seperti timeout/provider error
- planner task sekarang mendukung `priority`, `depends_on`, dan metadata retry yang lebih kaya
- runtime job queue lokal dan command `jobs` / `worker` untuk pemrosesan job eksplisit
- CLI subcommand resmi:
  - `otonomassist setup`
  - `otonomassist status`
  - `otonomassist doctor`
  - `otonomassist config status`
  - `otonomassist config setup`
  - `otonomassist chat`
  - `otonomassist run "<message>"`
  - `otonomassist telegram`
- dokumen operasional `OPERATIONS.md`
- regression test untuk:
  - stabilitas loop otonom
  - Telegram authorization
  - AI provider failure path
  - setup wizard
  - config doctor/status

### Changed

- `research` ditingkatkan menjadi skill riset yang date-aware, context-aware, dan mengembalikan data terstruktur
- output lintas skill mulai distandardisasi melalui structured result envelope dan formatter universal
- `research`, `workspace`, `planner`, `memory`, dan `self-review` sekarang mengikuti pola result envelope
- `Assistant` sekarang memisahkan produksi data hasil dari presentasi output
- CLI dipindahkan ke model subcommand, sambil mempertahankan compatibility alias lama
- README, ARCHITECTURE, dan SKILL_FORMAT disinkronkan dengan runtime saat ini

### Security

- credential runtime sekarang bisa fallback dari env ke encrypted local secrets
- Telegram authorization memakai policy fail-closed dengan owner/approved gating
- executor planner-task dibatasi untuk mencegah mutasi otomatis pada area sensitif seperti `secrets` dan `profile`
- state penting seperti planner dan secrets ditulis secara atomik untuk mengurangi risiko file parsial

### Stability

- `executor` mengenali lebih banyak prefix native seperti `research`, `runner`, dan `secrets`
- `self-review` mendedupe follow-up task terbuka
- `runner until-idle` sekarang menjalankan refleksi di setiap langkah
- lesson identik didedupe di recent window
