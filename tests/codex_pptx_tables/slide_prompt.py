"""Live slide structure exercise after the scanned table has been restored."""

INSTRUCTIONS = """
4s. Exercise slide structure. Before every mutation, completely read read_pptx at
    the current revision (follow next_slide_offset); after each mutation read it
    again. Preserve the original table and its slide identity exactly.
    Discover read_pptx_layouts and locate the destination layout with type blank.
    Discover each operation contract, then perform THREE mutations:
    (1) add_pptx_slides at index=1 with TWO slides using that layout. Each contains
        exactly one textbox at left=100000,top=100000,width=6000000,height=550000.
        First text: 'TEMP SLIDE 007 µg', font_size_pt=14,bold=true,italic=false.
        Second text: 'SECOND +0.00', font_size_pt=14,bold=false,italic=true.
        These are temporary exercise labels, not transcribed source content.
        Read COMPLETE shape JSON for BOTH new textboxes, preserving their evidence.
    (2) reorder_pptx_slides with all three actual slide_id/part keys in order:
        second temporary slide, original scanned-table slide, first temporary slide.
        Read COMPLETE shape JSON for the original table at this revision.
    (3) delete_pptx_slides with both temporary slide keys at the current revision.
        Re-read the final single-slide listing and COMPLETE original table JSON.
        Verify at least one full temporary shape reference after deletion, as
        historical evidence. Deleted package parts remain; no secure erasure claim.
    The auditor inspects every intermediate PPTX for slide order/IDs, exact temporary
    text/format, preserved original table/layout/media, relationships and package XML.
    This does not replace rendering the entire presentation in a viewer.
"""
