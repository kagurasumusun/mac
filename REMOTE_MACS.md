# Remote Macs (session record)

This file records the current known Upterm sessions and the local helper/key paths used in this workspace.
It stores **connection metadata only**, not private key contents.

## Local key / helper paths

- private key path: `/home/user/.ssh/upterm_test_ed25519`
- current-host helper (historical): `/home/user/cg_upterm.py`
- legacy-host helper (historical): `/home/user/cg_upterm_legacy.py`
- generic session helper: `/home/user/generic_upterm.py`

## Current validation host

- session: `z4InTbNySiFAh5OZVudP`
- ssh target: `z4InTbNySiFAh5OZVudP@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `15.7.7`
- observed default Xcode: `16.4 (16F6)`

Direct command form:

```bash
ssh -i /home/user/.ssh/upterm_test_ed25519 \
  -o IdentitiesOnly=yes -tt \
  z4InTbNySiFAh5OZVudP@uptermd.upterm.dev
```

## Additional analysis host

- session: `LUnMD48Mddy4PP4KeqJX`
- ssh target: `LUnMD48Mddy4PP4KeqJX@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `15.7.7` (`24G720`)
- observed default Xcode: `16.4 (16F6)`
- observed installed Xcodes include `16.0`–`16.4` and `26.0`–`26.3`

Direct command form:

```bash
ssh -i /home/user/.ssh/upterm_test_ed25519 \
  -o IdentitiesOnly=yes -tt \
  LUnMD48Mddy4PP4KeqJX@uptermd.upterm.dev
```

## Legacy reference host

- session: `ZrWtAfDSvKdWHtrrmfNR`
- ssh target: `ZrWtAfDSvKdWHtrrmfNR@uptermd.upterm.dev`
- repo path: `/Users/runner/work/mac/mac`
- observed OS: macOS `14.8.7`
- observed default Xcode: `15.4 (15F31d)`
- observed installed Xcodes: `15.0`–`15.4`, `16.1`–`16.2`

Direct command form:

```bash
ssh -i /home/user/.ssh/upterm_test_ed25519 \
  -o IdentitiesOnly=yes -tt \
  ZrWtAfDSvKdWHtrrmfNR@uptermd.upterm.dev
```

## Notes

- Upterm sessions are temporary and may expire; update this file when new sessions are issued.
- Do not commit private key material itself.
- The authoritative continuation record remains:
  - `CONTINUATION_MEMO_2026-07-13.md`
  - `HANDOFF.md`
  - `SESSION_HANDOFF_COMPLETE.md`
  - `PROJECT_STATE.json`
