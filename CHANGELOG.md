# Changelog

Dokumen ini merangkum perubahan penting yang sudah mendarat di OtonomAssist.

## Unreleased

## v1.1.6

### Changed

- clarified installer lifecycle into explicit `install`, `reinstall`, and `uninstall` modes
- `install` now prompts for `Y/n` confirmation before switching into implicit reinstall when an existing runtime is detected
- setup wizard now configures optional monitoring dashboard settings during first-run:
  - enabled/disabled
  - access mode
  - port
  - admin API URL
- `doctor --json` and provider diagnostics now mask API key values instead of returning plaintext secrets

### Validation

- Windows smoke passed for:
  - `install`
  - implicit reinstall confirmation
  - `uninstall`
- Linux smoke passed in WSL for:
  - `install`
  - implicit reinstall confirmation
  - `uninstall`
- `pytest -q tests/test_setup_wizard.py tests/test_public_package.py` -> `83 passed`

## v1.1.5

### Changed

- added installer preflight dependency checks at the start of install on Windows and Linux
- installer now verifies Python version compatibility before runtime install begins
- installer now verifies `venv/ensurepip` support before creating the real application venv
- Linux installer now fails clearly when non-interactive sudo is required for missing dependencies

### Validation

- Windows native install smoke passed with preflight checks
- Linux native install smoke passed in WSL with preflight checks
- `pytest -q tests/test_setup_wizard.py tests/test_public_package.py` -> `82 passed`

## v1.1.4

### Changed

- moved user installs to native OS application directories for Cadiax runtime binaries
- made monitoring dashboard placement explicit under the native app root on Windows and Linux
- unified the recommended service model around `cadiax service run cadiax`
- made Telegram an optional integrated runtime controlled by user settings instead of a separate primary service target
- hardened the Linux installer to detect missing `venv` support before runtime install

### Validation

- Windows native install smoke passed
- Linux native install smoke passed in WSL
- dashboard native path placement verified on both platforms
- `pytest -q tests/test_setup_wizard.py tests/test_public_package.py` -> `82 passed`

## v1.1.2

### Changed

- promoted `cadiax` as the primary public package namespace
- switched public CLI entrypoints to `cadiax` and `cadiax-telegram`
- aligned public docs and install flow with the Cadiax name
- added first-run installer scripts for Windows and Linux

### Compatibility

- retained `otonomassist` as a compatibility shim for legacy imports
- retained legacy CLI aliases during the migration window
- accepted `CADIAX_*` as public environment variable aliases while keeping legacy mappings

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
- worker runtime sekarang mendukung mode `until-idle`, cycle terjadwal, dan pencatatan status run terakhir
- section `[Runtime]` ditambahkan ke `doctor/status` untuk audit queue worker
- command `metrics` dan file agregat `execution_metrics.json` untuk observability ringan
- admin API read-only lokal untuk status, metrics, jobs, dan history
- scheduler runtime dengan state persisten dan command CLI `scheduler`
- admin API sekarang mendukung token auth opsional via `OTONOMASSIST_ADMIN_TOKEN`
- retrieval memori sekarang memakai hybrid exact match + token overlap untuk konteks dan search memory
- trust boundary skill eksternal sekarang aman-by-default lewat policy `approval-required`
- command `external approve` dan `external reject` ditambahkan untuk mengendalikan loading skill eksternal
- capability declaration untuk asset eksternal sekarang diaudit dan diperlukan sebelum approval
- allowlist capability eksternal sekarang dienforce lewat `OTONOMASSIST_EXTERNAL_CAPABILITY_ALLOW`
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
