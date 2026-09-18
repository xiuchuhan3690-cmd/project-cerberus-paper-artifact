# Dependencies

The tested `python reproduce/check_public.py` quick path uses Python 3.12+ and the standard library only. No Z3, Java, TLC, native DLL, network service, VM, or credential is required for those thirteen checks. This is a subset of historical reproduction. Apache-2.0 applies to the author-controlled contents included in this derivative; the upstream tools below keep their own licenses and are not bundled.

Historical optional dependencies, **not bundled** here:

| Component | Historically recorded version / source | Recorded digest | Role |
| --- | --- | --- | --- |
| Z3 / `z3-solver` | 5.1.0 / wheel 5.1.0.0, [official Z3 project](https://github.com/Z3Prover/z3) and [PyPI package](https://pypi.org/project/z3-solver/) | Historical wheel SHA-256 `1561efd36e06f4cb7cbf11b63a2fba8fc8fdeb9c5754df90c84f9bd7a4864552`, from private `manifests/Z3_Dependency_Manifest_v1.json` | Finite algebra/SMT obligations in private historical runs. |
| TLA+ tools / TLC | 1.8.0, [official release](https://github.com/tlaplus/tlaplus/releases/tag/v1.8.0) | Historical JAR SHA-256 `eabd140a70f49eb9305a3bd3f3df944eddf87e5a90d329789085f8953a80533a`, from private `manifests/TLA_TLC_Dependency_Manifest_v1.json` | Historical cutover/recovery model checking. |

Acquire optional tools from official upstream sources and verify the version/digest against the intended artifact. The recorded hashes identify historical binaries; a changed upstream rebuild may differ. No third-party binary redistribution is authorized by this derivative. See `THIRD_PARTY_NOTICES.md`.
