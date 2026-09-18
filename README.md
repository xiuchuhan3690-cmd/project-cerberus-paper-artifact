# Cerberus — bounded paper artifact (private candidate)

Cerberus studies authority discontinuity across a compromised trust epoch: selected typed state may cross into a new domain, but old authority ancestry may not. This is a **sanitized derivative for paper review**, not the authoritative M0–M8/RP1 historical archive, a production system, or an Active Directory recovery product. The repository is private pending author license and release decisions.

## Paper

*Cerberus: Authority-Sterile Recovery Across Compromised Trust Epochs* — XIU CHUHAN, Independent Researcher, Japan. Target: *Journal of Information Security and Applications* (JISA). No acceptance or publication is claimed. See [paper notes](paper/README.md).

## Core contribution and scope

The bounded composition combines transition-bound consume-and-mint authority, finite semantic conservation, sterile typed transfer, declared Authority Influence Mapping (AIM), a certificate-born parentless root, linearizable CutoverSlot and RecoverySlot abstractions, five epoch barriers, and fail-closed external-effect HOLD. The eight evaluated properties are TC-1, TC-2, TC-3, TC-4, TC-7, NTC-1, NTC-2 and NTC-3. They are preserved within declared finite/synthetic assumptions, **not** universally proven.

## Quick reproduction

Python 3.12+ (standard library only for the quick checks):

```sh
python reproduce/check_public.py
```

This checks ten public-derivative assertions, including eight-property inventory, copied-record structural verification, TC-3 values, three negative mutations, and inspection of three original counterexample records. See [reproduction instructions](reproduce/README.md) and [measured public result](PUBLIC_REPRODUCTION_REPORT.md). It does **not** run the private historical 642-test corpus.

## Artifact map

- `src/`: selected original finite model, canonical transition, M5 cutover, M6 recovery, and M7 integration code, copied without historical environment metadata. The quick path exercises a subset; the remaining modules are for inspection, not claimed as a complete standalone product.
- `models/`: representative original TLA+ cutover/recovery specifications and configurations, no bundled JAR.
- `verifier/`: implementation-separated RP1 declarative-evidence verifier excerpt.
- `counterexamples/`: three original representative negative-control records (TC-2, TC-4, NTC-1).
- `fixtures/`: three selected inert/synthetic finite inputs; no private machine metadata.
- `evidence/`: selected non-sensitive original finite result records. Their internal consistency can be inspected publicly; references to omitted private files are **not** rehashed here.
- `reproduce/`: newly written derivative checks and instructions.
- `PAPER_EVIDENCE_INDEX.md`: claim-to-public/private evidence classification.
- `private_provenance/`: logical source ref mapping without machine-local paths.

## Evidence boundary

Historical authoritative regression: **642/642 PASS** (private archive, unchanged corpus). Public derivative reproduction: **10/10 checks PASS** in the documented clean run; these are different tests. Historical raw archive materialization: **2,261/2,261 PASS**, **VERIFIED IN AUTHORITATIVE PRIVATE ARCHIVE**. The raw ZIP is not redistributed; this derivative is not byte-identical and cannot reconstruct every historical Windows raw-byte identity. M3 and M4 remain separate historical refs. See [claims and limitations](CLAIMS_AND_LIMITATIONS.md), [provenance](PROVENANCE.md), and [evidence index](PAPER_EVIDENCE_INDEX.md).

No AWS/payment-key-shaped negative fixture was copied into this candidate. `src/nlc/m5/t2/model.py` does contain two explicitly labeled `synthetic-share:` constructor values; they are nonfunctional local test material, not deployment credentials. Private historical tests also use synthetic, nonfunctional credential-shaped rejection inputs. No bundled third-party binary is redistributed here.

## Citation and license

Use [CITATION.cff](CITATION.cff) for authorship. **No public reuse license has been selected.** See [author license decision](AUTHOR_LICENSE_DECISION_REQUIRED.md). Do not interpret private candidate availability as permission to use or redistribute.
