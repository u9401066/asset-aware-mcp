"""Require actual whole-slide image review after the scanned-table edits."""

INSTRUCTIONS = """
4r. Discover render_pptx_slide. Render and VIEW the final current scanned-table
    slide at render_size=1024 with its explicit revision and exact pptx_slide_key.
    Compare it visually to the original scanned PDF: check every header/value,
    merged title, readable text, overlap and clipping. Read history to find the
    earlier revision in which the first data Count was temporarily '008'. Read
    read_pptx at that historical revision to obtain its slide key, then render and
    VIEW that historical slide too. Compare the visible output with native shape
    readback; report if overlapping tables hide the edited Count. Do not assume a
    text edit must be visible, and do not change history. This is LibreOffice output,
    not a check in Microsoft PowerPoint. If you see a defect, describe it precisely.
    Add visual_review to the final JSON: scope='static_libreoffice_slide_preview',
    reviewed_revisions (all distinct PPTX revisions whose images you viewed),
    findings (nonempty list with concrete observations), powerpoint_checked=false.
"""
