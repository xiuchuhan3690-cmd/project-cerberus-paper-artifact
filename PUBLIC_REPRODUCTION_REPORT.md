# Public derivative clean reproduction — 2026-09-18

- Environment: Windows NT 10.0.26200.0; Python 3.12.14; Python standard library only for this workflow. No Z3/TLA+/Java binary was used.
- Procedure: copy this final derivative candidate into a new disposable directory, then from its root run `python reproduce/check_public.py` and `python -m compileall -q src verifier reproduce`.
- Result: **10/10 public-derivative checks PASS**, 0 failures, 0 errors, test process exit 0; selected Python source compilation exit 0. Wall-clock for both commands: 0.421 seconds; unittest execution: 0.017 seconds. The clean copy contained 124 non-cache files.
- Checks include model vocabulary, eight-property inventory, copied RP1 record consistency, three negative verifier mutations, TC-3 recorded values, M8-T3 projection limit, Gate E record, and three representative original negative records.
- This does **not** reproduce the authoritative private 642/642 regression, 2,261/2,261 raw archive verification, original TLC/Z3 runs, full D1–D9 regeneration, or omitted historical provenance target-byte checks. Those numbers remain **VERIFIED IN AUTHORITATIVE PRIVATE ARCHIVE** only.
- No network, credentials, VM, external effect, Product P1+, or authoritative workspace was used.
