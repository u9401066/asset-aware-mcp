# Verified redundant PDF stream lengths

The real NASA Apollo 11 corpus has 359 QPDF warnings: image-stream dictionaries
contain the same direct integer `/Length` twice. Rejecting every warning prevents
read/region/evidence operations on this unchanged historical scan. Accept only a
mechanically proven equivalent representation; preserve original bytes and report
the interpretation. This does not enable general PDF repair or suppress warnings.

Before accepting any warning:

- Require the exact recognized duplicate `/Length` diagnostic; changed diagnostic
  wording, other keys/warnings, unresolved objects and compressed objects fail.
- Resolve the object through QPDF's xref table and independently parse its original
  bounded stream dictionary. Require the diagnostic offset to identify this root
  dictionary; nested duplicate keys do not qualify.
- Read every top-level `/Length` occurrence, including escaped PDF names, as a
  nonnegative direct integer. All values must agree. Reject indirect lengths,
  conflicting values, duplicate other/nested keys, unsupported string/hex values,
  excess nesting/tokens/header bytes, and malformed syntax.
- Require every declared length to match QPDF's raw stream length AND the exact
  original bytes after `stream` EOL through the specified length to `endstream`.
  No recovery, stream decoding or reserialization is used during reads.
- Recheck newly generated QPDF warnings; only the already verified diagnostics
  may be consumed. Every qualifying warning must be accounted for.

Expose a bounded `parser_checks` observation in PDF listings and full page records:
policy identifier, verified stream/declaration counts, proof digest over checked
object IDs, original dictionary spans/hashes and lengths, and the explicit statement
that source bytes are preserved. Normal PDFs retain their current representations.
The digest summarizes the deterministic check; it is not a semantic verdict.

Existing requested page mutations may serialize equivalent stream dictionaries
with a single Length. Record `canonicalized_equal_duplicate_stream_lengths` in
the operation repairs. Copying from such a source records the same normalization.
Retain existing page/object/form/render checks, historical refs, immutable original
source and explicit publication/writeback. Checked output must have no remaining
parser observations. Do not silently normalize a read or pretend raw bytes match.

Regression evidence: independent handcrafted PDFs cover equal/conflicting values,
comments, escaped names, nested distractions, indirect lengths, stream boundaries,
unknown diagnostics and bounded input; source/region CRUD on unchanged NASA PDF
must then pass through actual SDK2. Actual Codex remains separate visual evidence.

References: [pikepdf main API](https://pikepdf.readthedocs.io/en/latest/api/main.html),
[QPDF checks](https://qpdf.readthedocs.io/en/stable/cli.html#option-check).
Warning text is not a stable API; fail closed if an upstream update changes it.
Public1.4.0 / Unreleased1.4.x; no new version or tag.
