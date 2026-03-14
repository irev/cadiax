# TUI Wave Next

Dokumen ini menurunkan hasil `TUI_CLI_COVERAGE_MATRIX.md` menjadi urutan implementasi praktis.

## Wave N+1

Fokus:

- runtime operations
- observability
- service parity dasar

Deliverables:

1. layar `Jobs`
2. layar `Worker`
3. layar `Scheduler`
4. layar `Metrics`
5. layar `History`
6. layar `Events`
7. action service dasar:
   - status
   - write wrappers
   - show target summary

## Wave N+2

Fokus:

- governance
- workspace/startup inspection
- privacy/operator controls

Deliverables:

1. layar `Privacy`
2. layar `Startup`
3. layar `Bootstrap`
4. layar `Agents`
5. layar `Notify`

Status:

- `Privacy`: selesai
- `Startup`: selesai
- `Bootstrap`: selesai
- `Agents`: berikutnya
- `Notify`: berikutnya

## Wave N+3

Fokus:

- service/operator mutations
- governance parity lanjutan
- extension surfaces

Deliverables:

1. layar `Agents`
2. layar `Notify`
3. action aman untuk `Worker` / `Scheduler`
4. action service dasar untuk `admin-api` / `conversation-api`
5. extended `Channels` for `email` / `whatsapp`

## Wave N+4

Fokus:

- extension surfaces
- deeper audit/runtime parity

Deliverables:

1. layar `External`
2. layar `Skills`
3. layar `Heartbeat`
4. layar `Proactive`
5. privacy/bootstrap advanced actions
