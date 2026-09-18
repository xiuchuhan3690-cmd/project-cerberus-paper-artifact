# Quick public-derivative reproduction

From the repository root, use Python 3.12+:

```sh
python reproduce/check_public.py
python -m compileall -q src verifier reproduce
```

No package installation is needed. The script executes thirteen checks: selected finite vocabulary, eight-property record inventory, RP1 copied-record verifier, three deliberate negative mutations, TC-3 captures, M8-T3 projection boundary, Gate E status, three representative original counterexample records, and executable recovery retry/HOLD/old-carrier checks. `OK` means these **publicly available checks** passed. It does not rerun TLC/Z3, regenerate nine scenario bundles, validate omitted provenance target hashes, or reproduce the unchanged historical 642-test regression.

The clean-run environment, command, result and timing are in `PUBLIC_REPRODUCTION_REPORT.md`. Optional historical-tool versions and official acquisition links are in `DEPENDENCIES.md`; no untested optional command is presented as a passing reproduction step.
