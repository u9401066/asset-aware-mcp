"""Additional live workflow for revision-pinned source-to-table provenance."""

INSTRUCTIONS = """4b. After deletion, read the retained FIRST table COMPLETELY at the latest
    deck revision. Record that exact table as derived from the original PDF page.
    Discover record_derivation/read_derivations/retract_derivation/verify_derivation.
    Read the complete empty derivation ledger, retaining derivations_sha256.
    record_derivation needs asset_id, expected_derivations_sha256 and derivation:
    target is the full FINAL table reference; sources is [the full source page ref].
    agent='Codex CLI'; activity describes your scanned-table transcription.
    Review only what you actually checked. rendered_layout='not_checked' and
    formula_results='not_applicable'; notes='Initial transcription review'.
    Read the entire resulting ledger through all chunks, verifying UTF-8 SHA256.
    Append a replacement assertion with supersedes=the first derivation_id and
    notes='Rechecked literal strings, leading zeros, signs and separators'.
    Use the latest ledger hash. Both assertions retain the SAME exact final target
    and source page references. Read the full updated ledger.
    Add a third temporary assertion with activity='Temporary review entry',
    same endpoints and review values; read the ledger and retract ONLY this third
    assertion with agent='Codex CLI', reason='Remove temporary review entry'.
    Read the complete final ledger. Verify first/second/third derivation IDs:
    the first and third must be inactive, the second active, with valid references.
    Preserve failures/recoveries honestly. The server validates bytes/locators;
    the agent identity and semantic review are caller assertions, not certification.
    Final wiki export must include the active source-to-table assertion, exact
    source PDF attachment and full ledger. Never alter the source PDF.
"""
