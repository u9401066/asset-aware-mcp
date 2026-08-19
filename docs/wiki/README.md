# Asset-Aware MCP Wiki Source

This directory is the versioned source for the GitHub Wiki page set. `Home.md`
is the wiki entry page and `_Sidebar.md` is the GitHub Wiki sidebar.

The wiki is initialized and published at
<https://github.com/u9401066/asset-aware-mcp/wiki>. This versioned directory is
the reviewed source used to synchronize its Markdown pages; do not treat a
separate local wiki clone as the source of truth.

The current page set intentionally has no raster-diagram dependency. The GitHub
Pages reader is generated from these files with
`python3 scripts/build_docs_site.py`; run the same command with `--check` before
publishing. Synchronize the backing `asset-aware-mcp.wiki.git` repository only
from a reviewed commit, then verify the remote page set and links.
