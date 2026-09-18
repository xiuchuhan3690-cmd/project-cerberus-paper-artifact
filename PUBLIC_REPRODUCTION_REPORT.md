# Public derivative clean reproduction — 2026-09-18

- Environment: Windows NT 10.0.26200.0; Python 3.12.14; Python standard library only for this workflow. No Z3/TLA+/Java binary was used.
- Procedure: clone the Apache-2.0-licensed derivative candidate into a new disposable directory, then from its root run `python reproduce/check_public.py` and `python -m compileall -q src verifier reproduce`.
- Result: **13/13 public-derivative checks PASS**, 0 failures, 0 errors, test process exit 0; selected Python source compilation exit 0. Unittest execution: 0.018 seconds. The clean copy contained 127 tracked non-cache files. The earlier pre-license candidate also passed 13/13 in 0.019 seconds; its 0.367-second combined wall-clock measurement is not presented as a measurement of this licensed revision.
- Checks include model vocabulary, eight-property inventory, copied RP1 record consistency, three negative verifier mutations, TC-3 recorded values, M8-T3 projection limit, Gate E record, three representative original negative records, and executed recovery retry/HOLD/old-carrier checks.
- This does **not** reproduce the authoritative private 642/642 regression, 2,261/2,261 raw archive verification, original TLC/Z3 runs, full D1–D9 regeneration, or omitted historical provenance target-byte checks. Those numbers remain **VERIFIED IN AUTHORITATIVE PRIVATE ARCHIVE** only.
- No network, credentials, VM, external effect, Product P1+, or authoritative workspace was used.
