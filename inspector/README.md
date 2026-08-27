# Tier 1 Inspector

Static, non-executing file analysis. A sample goes in; structured JSON + PNG
previews come out. **Nothing executes the sample** — the safety boundary is the
container isolation (see CLAUDE.md -> File Analysis), not
parser correctness.

## Layout
```
inspector/
  contract.py        # shared types, flag constants, InspectorResult (zero deps)
  common.py          # hashes, entropy, magic-vs-ext mismatch, IOC regex
  router.py          # type detection + dispatch + recursion entry point
  entrypoint.py      # reads job JSON on stdin -> runs router -> writes JSON on stdout
  analyzers/
    verdict.py       # deterministic verdict table (see CLAUDE.md -> File Analysis)
    pdf.py office.py script.py lnk.py pe.py archive.py email.py html.py
  Dockerfile         # spawned PER JOB by inspector-runner, never long-running
  requirements.txt   # pure parsers only — NO PSDecode/box-ps, NO yara
  tests/             # benign, generated-at-test-time fixtures
```

## How it runs in production
`inspector-runner` (sibling dir) spawns this image per job with
`--network none --read-only --cap-drop ALL --security-opt no-new-privileges`
plus memory/pids/cpu caps, feeds the job on stdin, collects stdout, and destroys
the container. CoPilot never talks to Docker directly.

## Deobfuscation is pure-static
The script analyzer unwinds base64 `-enc`, concatenation, char-arrays, and
gzip/deflate to a bounded fixpoint **without ever running the script**. What it
can't statically resolve (live `IEX` of a runtime value) is surfaced as
`deobfuscation_incomplete` — itself the Tier 2 escalation signal. PSDecode/box-ps
are banned from the image because they execute scripts in an instrumented
interpreter (see CLAUDE.md -> File Analysis).

## Known-malware naming
No bundled YARA (nothing to curate/rot). Naming comes from the optional ClamAV
sidecar (freshclam-maintained) and P5 hash reputation (SOCFortress TI first).

## Dev status
Pure-logic paths (deobfuscation, verdict, IOC, normalizer, type detection,
recursion) are implemented and self-checked. Tool-backed paths (pdfid,
LibreOffice, oletools, capa/FLOSS) degrade gracefully when the binary is absent
and are exercised in the image build test (WI-1). No DB, no live services touched.
```
