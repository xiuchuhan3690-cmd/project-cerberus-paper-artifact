# Logical historical source map

Authoritative private Git identities (not public repository URLs):

- main: `2e61380b298a708bca22ff742cfcfab6b977601e`
- historical-m3: `c8dedc7f03c2e9c3607737b66f971a69ff768c23`
- historical-m4: `7d48a30863bc9fb3097e70ae9c348ef21f6acfcf`

| Derivative path | Private logical source | Treatment |
| --- | --- | --- |
| `src/nlc/formal/*` | `main:nlc/formal/*` | Selected original bytes, screened before copy. |
| `src/m1/*` | `main:m1/*` | Selected original bytes needed by formal package imports. |
| `src/nlc/m5/*`, `src/nlc/m6/*`, `src/nlc/m7/*` | `main:nlc/m5/*`, `main:nlc/m6/*`, `main:nlc/m7/*` | Selected original cutover/recovery/integration Python modules; no private environment records or bundled runtimes. The public quick path exercises only a subset. |
| `models/*` | `main:tla/*` selected `.tla`/`.cfg` files | Original specification/configuration bytes; no JAR. |
| `verifier/rp1_verifier.py` | `main:nlc/m8/t4/verifier.py` | Original implementation-separated verifier bytes, renamed for reader-facing layout. |
| `evidence/rp1_package.json` | `main:NLC-RP1_v1.0/package.json` | Original bytes; references to omitted historical objects remain logical identifiers. |
| `evidence/*.json` (other files) | `main:manifests/<same basename>` | Selected original record bytes. Public checks do not rehash omitted referenced files. |
| `counterexamples/t3/*` | `main:counterexamples/t3/*` | Three representative original negative records, not the full toggle corpus. |
| `fixtures/*` | `main:fixtures/<same basename>` | Three selected original inert/synthetic finite inputs. |
| `reproduce/*`, public documentation | New derivative material | Not part of historical freeze or private raw-byte archive. |

The private M3 and M4 lines remain independent; this derivative does not merge them or imply their entire trees are public. The private raw archive, machine-local historical material, Product P1+, and bundled third-party binaries are excluded. No machine-local filesystem path is recorded here.
