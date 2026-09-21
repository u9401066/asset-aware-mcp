# Native raster assets — implementation contract

Status: internal kernel in development; public version **1.4.0**, next consolidated
release **1.4.1**. No image operations are advertised through MCP yet.

A raster asset retains its exact source bytes and immutable revisions. Frame
records describe the decoder's main frame sequence, with zero-based locators,
stored/displayed dimensions, EXIF orientation, sample precision, pixel hashes and
typed metadata. PNG/APNG, JPEG, TIFF, GIF, WebP, BMP and AVIF are the initial
decoder formats. Optional decoder availability remains a runtime constraint.

The projection is not a claim to understand every TIFF sub-IFD, private field,
thumbnail or layer. Animated frames describe composited display frames. APNG's
optional default image is a separate frame. Palette colors and transparency are
part of displayed pixel identity. Unknown or reduced source precision must never
be presented as proven source-sample preservation.

Frame and region references bind asset ID, source SHA-256, complete locator and
canonical record hash. Regions use EXIF-oriented displayed-frame fractions with a
top-left origin; bounds round outward to whole pixels. Render size/color policy
does not change region identity. PNG previews are RGBA8, optionally transformed
from embedded ICC to sRGB, with no inferred HDR intensity scaling.

Creation offers explicit RGBA canvases. Extraction creates a new PNG/TIFF from a
complete source-frame reference and optional region. TIFF composition creates a
new ordered frame sequence from complete references, with explicit decoded-pixel
or RGBA8 projection and `pixels_only` metadata policy. These derivatives retain
the original asset and report omitted metadata. Each encoded output is reopened
and checked for exact requested frame count, geometry, sample bytes and decoded
colors. Reordering, insertion and deletion can be expressed through a new composed
candidate; no animation timing is invented for a TIFF sequence.

In-place image revisions accept an independently registered candidate with the
same detected format. A plan pins the source catalog and full candidate file
reference, maps or deletes every old frame, and maps or inserts every new frame
exactly once. Mapped frames explicitly preserve or replace decoded pixels and
decoder metadata. The committed bytes are exactly the checked candidate bytes;
the MCP must not silently re-encode an original to satisfy an edit.

Decoder workers have time, memory, input, pixel, metadata and result bounds.
Malformed/truncated TIFF main-directory chains cannot be accepted as shorter
documents. Oversized output or failed readback stops before repository mutation.
MCP handles identity, structural checks and inspectable receipts. The Agent checks
actual images, meaning, color, frame correspondence and metadata changes, then
coordinates corrections. This kernel alone does not complete MCP, evidence,
citations, Wiki, SDK2 or actual-Agent integration.

References informing these choices:

- [Pillow file-format behavior](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- [libvips multipage and animated images](https://github.com/libvips/libvips/blob/master/doc/multipage-and-animated-images.md)
