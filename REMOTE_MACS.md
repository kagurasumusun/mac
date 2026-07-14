# Remote Macs (session record)

This file records the current known Upterm sessions and the local helper/key paths used in this workspace.
It stores **connection metadata only**, not private key contents.

## Local key / helper paths

- private key path: `/home/user/.ssh/upterm_test_ed25519`
- current-host helper (historical): `/home/user/cg_upterm.py`
- legacy-host helper (historical): `/home/user/cg_upterm_legacy.py`
- generic session helper: `/home/user/generic_upterm.py`

## Current validation host

- session: `NoqRgiONpDaSlIzApHRa`
- ssh target: `NoqRgiONpDaSlIzApHRa@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `26.4`
- observed default Xcode: `26.5 (17F42)`
- note: active host for the 2026-07-14 second follow-up (brandassets target-device-tv and iconstack fixture discovery)

Direct command form:

```bash
ssh -i /home/user/.ssh/upterm_test_ed25519 \
  -o IdentitiesOnly=yes -tt \
  NoqRgiONpDaSlIzApHRa@uptermd.upterm.dev
```

## Previous validation host

- session: `QX8mPOpocAXnJg0BOxaB`
- ssh target: `QX8mPOpocAXnJg0BOxaB@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `26.4`
- observed default Xcode: `26.5 (17F42)`
- note: used for the 2026-07-14 first follow-up and earlier push/revalidation

## Push/auth host used previously

- session: `ensGhYjemxYDEzOgilri`
- ssh target: `ensGhYjemxYDEzOgilri@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `26.4`
- observed default Xcode: `26.5 (17F42)`
- note: used successfully to apply patch and push `f83f380` to `origin/actool`

## Additional analysis host

- session: `LUnMD48Mddy4PP4KeqJX`
- ssh target: `LUnMD48Mddy4PP4KeqJX@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `15.7.7` (`24G720`)
- observed default Xcode: `16.4 (16F6)`
- observed installed Xcodes include `16.0`–`16.4` and `26.0`–`26.3`
- note: returned `Permission denied (publickey)` in the 2026-07-14 follow-ups; re-test before use

## Legacy reference host

- session: `ZrWtAfDSvKdWHtrrmfNR`
- ssh target: `ZrWtAfDSvKdWHtrrmfNR@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `14.8.7`
- observed default Xcode: `15.4 (15F31d)`
- observed installed Xcodes: `15.0`–`15.4`, `16.1`–`16.2`
- note: returned `Permission denied (publickey)` in the 2026-07-14 follow-ups; re-test before use

## Older session retained for history

- `z4InTbNySiFAh5OZVudP` — older macOS 15.7.7 / Xcode 16.4 validation host from the previous continuation phase

## Notes

- Upterm sessions are temporary and may expire; update this file when new sessions are issued.
- Do not commit private key material itself.
- The authoritative continuation record remains:
  - `CONTINUATION_MEMO_2026-07-13.md`
  - `HANDOFF.md`
  - `SESSION_HANDOFF_COMPLETE.md`
  - `PROJECT_STATE.json`
