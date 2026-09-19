// Document-context citeproc-js bridge. Only bundled code is executed.
"use strict";
const CSL = require("./csl_resources/citeproc.js");
const crypto = require("node:crypto");
const INPUT_LIMIT = 4 * 1024 * 1024;
const OUTPUT_LIMIT = 8 * 1024 * 1024;
let chunks = [], length = 0;
process.stdin.on("data", chunk => {
  length += chunk.length;
  if (length > INPUT_LIMIT) { process.stderr.write("CSL input byte limit"); process.exit(2); }
  chunks.push(chunk);
});
process.stdin.on("end", () => {
  try {
    if (Number(process.versions.node.split(".")[0]) < 20) throw new Error("Node.js >=20 is required");
    const input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    chunks = [];
    const document = input.document;
    const warnings = new Set();
    CSL.debug = message => {
      if (warnings.size >= 100) throw new Error("Too many CSL diagnostics");
      warnings.add(String(message).slice(0, 1000));
    };
    CSL.error = message => { throw new Error(String(message)); };
    function render(format) {
      const key = id => "item-" + crypto.createHash("sha256").update(id, "utf8").digest("hex");
      const originalIds = new Map(document.items.map(item => [key(item.id), item.id]));
      const items = new Map(document.items.map(item => [key(item.id), {...item, id: key(item.id)}]));
      const sys = {
        retrieveItem: id => {
          if (!items.has(String(id))) throw new Error("Unknown CSL item ID");
          return JSON.parse(JSON.stringify(items.get(String(id))));
        },
        retrieveLocale: language => {
          const key = language === "en" ? "en-US" : language === "zh" ? "zh-CN" : language;
          if (!Object.hasOwn(input.locales, key)) throw new Error("Unbundled CSL locale: " + language);
          return input.locales[key];
        }
      };
      const processor = new CSL.Engine(sys, input.style, document.locale, true);
      processor.setOutputFormat(format);
      processor.updateUncitedItems(document.uncited_ids.map(key));
      const preceding = [], rendered = [];
      for (const cluster of document.clusters) {
        const citation = {
          citationID: key(cluster.id),
          properties: { noteIndex: cluster.note_index },
          citationItems: cluster.cites.map(cite => ({
            id: key(cite.id), label: cite.label,
            ...(cite.locator === null ? {} : {locator: cite.locator}),
            prefix: cite.prefix, suffix: cite.suffix,
            "suppress-author": cite.suppress_author
          }))
        };
        const result = processor.processCitationCluster(citation, preceding, []);
        if (result[0].citation_errors && result[0].citation_errors.length) {
          throw new Error("CSL citation errors: " + JSON.stringify(result[0].citation_errors));
        }
        for (const update of result[1]) rendered[update[0]] = update[1];
        preceding.push([key(cluster.id), cluster.note_index]);
      }
      const bibliography = processor.makeBibliography();
      if (!bibliography || (bibliography[0].bibliography_errors || []).length) {
        throw new Error("CSL bibliography could not be rendered completely");
      }
      if (rendered.length !== document.clusters.length || rendered.some(x => typeof x !== "string")) {
        throw new Error("Incomplete CSL cluster updates");
      }
      return { citations: rendered, bibliography: bibliography[1], entry_ids: bibliography[0].entry_ids.map(ids => ids.map(id => originalIds.get(id))),
        bibliography_options: Object.fromEntries(Object.entries(bibliography[0]).filter(([key]) => !["entry_ids", "bibstart", "bibend", "bibliography_errors"].includes(key))) };
    }
    const text = render("text"), html = render("html");
    if (JSON.stringify(text.entry_ids) !== JSON.stringify(html.entry_ids)) throw new Error("CSL output mapping mismatch");
    const output = JSON.stringify({ text, html, warnings: [...warnings], processor_version: CSL.PROCESSOR_VERSION, node_version: process.version });
    if (Buffer.byteLength(output, "utf8") > OUTPUT_LIMIT) throw new Error("CSL output byte limit");
    process.stdout.write(output);
  } catch (error) {
    process.stderr.write(String(error.message || error).slice(0, 2000));
    process.exitCode = 1;
  }
});
