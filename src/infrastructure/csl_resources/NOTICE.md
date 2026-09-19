# Citation processor and style resources

The unmodified `citeproc.js` is Frank Bennett's citeproc-js 2.4.63, extracted from
the npm release with its published SHA-512 integrity verified. It is distributed
under the upstream dual CPAL-1.0-or-later / AGPL-3.0-or-later terms. Full upstream
LICENSE, CPAL and AGPL texts are retained next to it. These files retain their
upstream licenses; the repository's Apache license does not replace them.

Official Citation Style Language styles and locales retain their authors,
attribution and CC BY-SA 3.0 notices in each XML file and upstream README files.
`vancouver.csl` is the unmodified `nlm-citation-sequence.csl`, the independent
parent of upstream `vancouver-nlm`. APA is 7th edition; Chicago is 18th edition.
The official CSL-JSON input schema retains its upstream LICENSE.txt.

`manifest.json` pins exact source URLs, repository commits, byte counts and
SHA-256 hashes. Runtime rendering reads these bundled resources without network
requests. The project bridge (`../csl_worker.cjs`) is separate from upstream code.

Source projects: https://github.com/Juris-M/citeproc-js,
https://github.com/citation-style-language/styles,
https://github.com/citation-style-language/locales,
https://github.com/citation-style-language/schema.
