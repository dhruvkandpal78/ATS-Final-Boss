# Candidate artifact boundaries — October 2, 2026

## Problem and change

Candidate verification previously read each complete file into memory before
checking its digest. The subsequent loader also had unbounded reads. Manifest
parsing accepted duplicate keys/non-finite values, while the policy hash set
did not include source-span evidence code.

Candidate manifests now have a 256 KiB bound and must be unambiguous JSON
objects with the existing candidate feature contract and exactly the four
named artifact hashes. Independent pins and artifact hashes require 64-digit
SHA-256 syntax; hexadecimal case is normalized for comparison. Duplicate keys,
non-finite numbers and invalid/deeply nested JSON fail closed.

Named pickle artifacts are capped at 64 MiB each; threshold/model JSON artifacts
are capped at 1 MiB each. Initial verification hashes in chunks of at most
1 MiB. The loader reads a bounded exact-byte snapshot, checks its digest again
for a candidate, then deserializes that snapshot. Legacy local pickle reads
also use the bounds, but legacy mode has no candidate integrity claim and
remains disallowed in pinned private deployments.

The named directory and files must be non-linked regular filesystem entries;
symbolic links and Windows reparse entries are rejected. File descriptors are
checked before reading, with no-follow/nonblocking open flags where available.
Size growth or truncation during reading/hashing fails rather than accepting
an incomplete result. Extra files are not recursively scanned or certified;
the contract concerns the manifest and four named artifacts only.

`src/core/evidence.py` is now required in the policy source hash set. Old
five-file freezes fail the current contract. No old manifest or independent
pin is rewritten, no consumed holdout is reopened and no prior validation is
inherited automatically. Review/provision a new bundle for the intended source
revision and obtain its pin through the existing trusted approval process.

## Verification

Focused checks initially passed **36 tests**, with three Windows symlink cases
skipped because this host did not permit creating links. Tests cover malformed
pins, duplicate/non-object manifests, size bounds, exact artifact names,
special/link entries, streaming verification, evidence-source changes and
mutated bytes before deserialization. Additional regressions verify oversized
candidate and legacy weights never reach pickle deserialization.

The existing trusted local research candidate passed the new byte-integrity
contract unchanged; its four named artifacts total 1,696 bytes. Its old policy
freeze remains rejected. This is file-contract compatibility, not deployment
approval, full embedding/native-model compatibility or detector validation.

Full offline suite: **549 passed**, five platform/link skips and three
provisioned-model integration tests deselected. Subsequent focused checks:
**41 passed**, three Windows link-creation skips, including simulated growth
at initial hashing and at the loader's second read plus consistent uppercase
digest handling. No implementation changed after the full run; the later
focused run adds these edge-case tests. Scoped high-severity Bandit and
whitespace checks passed. Linux hosted verification remains pending for this
new revision; previous PR #11 merged after all hosted checks passed.

## Limits and publication

Pickle can execute code. These bounds are not a safe deserialization sandbox,
an authenticity claim, a physical-memory limit or proof against a hostile host.
Immutable access-controlled mounts, independent approved pins, trusted artifact
origins and customer release evidence remain required. Link/open protections
vary by platform; mutable parent paths and kernel/filesystem races are not
certified away. A small serialized model can allocate more memory when loaded
or evaluated; separate native-memory containment remains unverified.

Review rules, thresholds, learned weights, API responses and benchmark outcomes
are unchanged. No new accuracy, downstream benefit, fairness, customer pilot or
production-readiness claim. Published changes contain code/tests/docs only;
no personal PDFs, local model artifacts, raw responses, keys or private history.
