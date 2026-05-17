/* global marked, mermaid */

const DOC_PAGES = window.ASSET_AWARE_DOC_PAGES || [];
const embeddedContent = window.ASSET_AWARE_DOC_PAGE_CONTENT || {};
const DOC_STATS = window.ASSET_AWARE_DOC_STATS || {
  version: "0.7.0",
  tools: 30,
  resources: 13,
  endpoints: 43,
};
const LANGUAGE_STORAGE_KEY = "asset-aware-docs-language";
const SUPPORTED_LANGUAGES = ["en", "zh"];
const LANGUAGE_META = {
  en: { htmlLang: "en", label: "EN" },
  zh: { htmlLang: "zh-TW", label: "繁中" },
};
const NAV_GROUPS = [
  "start",
  "user",
  "evidence",
  "operations",
  "reference",
  "developer",
];
const UI_COPY = {
  en: {
    siteEyebrow: "Documentation",
    tagline: "Citation-ready document workflows for AI agents.",
    filterLabel: "Filter pages",
    filterPlaceholder: "PDF, DOCX, citation, VSIX...",
    sidebarNote:
      "Generated from docs/wiki and checked against the MCP code surface before release.",
    heroKicker: "Production docs for v{version}",
    heroCopy:
      "Task-first documentation for Asset-Aware MCP: install, document workflows, citation provenance, optional KG/RAG, VSIX setup, and release checks aligned with the current code.",
    menu: "Menu",
    outlineTitle: "On This Page",
    noPages: "No pages match this filter.",
    unableTitle: "Unable to load page",
    regenerate: "Run",
    regenerateSuffix: "to regenerate site content.",
    toolMetric: "MCP tools",
    resourceMetric: "MCP resources",
    endpointMetric: "endpoints",
    quickActions: {
      start: "Install",
      workflow: "Workflow chapters",
      kg: "KG / RAG",
      release: "Release checks",
    },
    status: {
      pdf: "PyMuPDF default",
      ragLabel: "RAG default",
      rag: "Ollama granite4.1:3b",
      kgLabel: "KG safety",
      kg: "LightRAG opt-in",
      releaseLabel: "Release gates",
      release: "CI + VSIX smoke",
    },
    groups: {
      start: "Start Here",
      user: "Document Workflows",
      evidence: "Evidence & Knowledge",
      operations: "Operations",
      developer: "Maintainers",
      reference: "Reference",
    },
  },
  zh: {
    siteEyebrow: "文件網站",
    tagline: "給 AI agents 使用的 citation-ready 文件工作流。",
    filterLabel: "篩選頁面",
    filterPlaceholder: "PDF、DOCX、citation、VSIX...",
    sidebarNote:
      "內容由 docs/wiki 生成，並在 release gate 中和 MCP tools/resources 程式面同步檢查。",
    heroKicker: "v{version} 正式文件",
    heroCopy:
      "以任務優先整理 Asset-Aware MCP：安裝、文件工作流、citation provenance、可選 KG/RAG、VSIX 設定與上線檢查都對齊目前程式碼。",
    menu: "選單",
    outlineTitle: "本頁內容",
    noPages: "沒有符合篩選條件的頁面。",
    unableTitle: "無法載入頁面",
    regenerate: "請執行",
    regenerateSuffix: "重新生成 site content。",
    toolMetric: "MCP tools",
    resourceMetric: "MCP resources",
    endpointMetric: "endpoints",
    quickActions: {
      start: "開始安裝",
      workflow: "流程章節",
      kg: "KG / RAG",
      release: "上線檢查",
    },
    status: {
      pdf: "預設 PyMuPDF",
      ragLabel: "RAG 預設",
      rag: "Ollama granite4.1:3b",
      kgLabel: "KG 安全性",
      kg: "LightRAG opt-in",
      releaseLabel: "上線 gate",
      release: "CI + VSIX smoke",
    },
    groups: {
      start: "開始",
      user: "文件流程",
      evidence: "證據與知識庫",
      operations: "維運與上線",
      developer: "開發者與維護者",
      reference: "參考",
    },
  },
};

const nav = document.getElementById("page-nav");
const filterInput = document.getElementById("nav-filter");
const filterLabel = document.getElementById("filter-label");
const docContent = document.getElementById("doc-content");
const pageOutline = document.getElementById("page-outline");
const pageTitle = document.getElementById("page-title");
const pageKicker = document.getElementById("page-kicker");
const navToggle = document.getElementById("nav-toggle");
const navClose = document.getElementById("nav-close");
const sidebar = document.getElementById("sidebar");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");
const siteEyebrow = document.getElementById("site-eyebrow");
const siteTagline = document.getElementById("site-tagline");
const sidebarNoteText = document.getElementById("sidebar-note-text");
const heroKicker = document.getElementById("hero-kicker");
const heroCopy = document.getElementById("hero-copy");
const toolMetricLabel = document.getElementById("tool-metric-label");
const resourceMetricLabel = document.getElementById("resource-metric-label");
const endpointMetricLabel = document.getElementById("endpoint-metric-label");
const toolMetricValue = document.getElementById("tool-metric-value");
const resourceMetricValue = document.getElementById("resource-metric-value");
const endpointMetricValue = document.getElementById("endpoint-metric-value");
const statusVersion = document.getElementById("status-version");
const statusPdf = document.getElementById("status-pdf");
const statusRagLabel = document.getElementById("status-rag-label");
const statusRag = document.getElementById("status-rag");
const statusKgLabel = document.getElementById("status-kg-label");
const statusKg = document.getElementById("status-kg");
const statusReleaseLabel = document.getElementById("status-release-label");
const statusRelease = document.getElementById("status-release");
const summaryBand = document.querySelector(".summary-band");
const statusStrip = document.querySelector(".status-strip");
const languageControls = Array.from(document.querySelectorAll("[data-lang]"));
const quickActionLinks = Array.from(document.querySelectorAll("[data-quick-action]"));
const markdownRenderer = window.marked;
let mermaidInitialized = false;
let activeLang = preferredLanguage();

if (markdownRenderer?.setOptions) {
  markdownRenderer.setOptions({
    gfm: true,
    breaks: false,
  });
}

function preferredLanguage() {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (SUPPORTED_LANGUAGES.includes(stored)) {
      return stored;
    }
  } catch (_error) {
    // Storage can be blocked in local or privacy-constrained contexts.
  }

  return "zh";
}

function persistLanguage(lang) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
  } catch (_error) {
    // The selected language still applies for the current session.
  }
}

function uiText(key) {
  return UI_COPY[activeLang]?.[key] || UI_COPY.en[key] || key;
}

function pageBySlug(slug) {
  return DOC_PAGES.find((page) => page.slug === slug);
}

function defaultSlugForLanguage(lang) {
  const translatedOverview = DOC_PAGES.find(
    (page) => page.group === "overview" && page.lang === lang,
  );
  return translatedOverview?.slug || "overview-zh";
}

function rawSlugFromHash() {
  return window.location.hash.replace(/^#\/?/, "").trim();
}

function currentSlug() {
  return rawSlugFromHash() || defaultSlugForLanguage(activeLang);
}

function pageText(page, key) {
  const localized = page[`${key}ByLang`];
  return localized?.[activeLang] || page[key];
}

function translatedSlugFor(page, lang) {
  if (!page) {
    return defaultSlugForLanguage(lang);
  }
  if (page.lang === "all" || page.lang === lang) {
    return page.slug;
  }

  const translated = DOC_PAGES.find(
    (entry) => entry.group === page.group && entry.lang === lang,
  );
  return translated?.slug || page.slug;
}

function pageMatchesLanguage(page) {
  return page.lang === "all" || page.lang === activeLang;
}

function closeSidebar() {
  sidebar.classList.remove("open");
  document.body.classList.remove("nav-open");
  if (sidebarBackdrop) {
    sidebarBackdrop.hidden = true;
  }
  navToggle.setAttribute("aria-expanded", "false");
}

function openSidebar() {
  sidebar.classList.add("open");
  document.body.classList.add("nav-open");
  if (sidebarBackdrop) {
    sidebarBackdrop.hidden = false;
  }
  navToggle.setAttribute("aria-expanded", "true");
}

function renderLanguageControls() {
  languageControls.forEach((button) => {
    const isActive = button.dataset.lang === activeLang;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function localizeStaticText() {
  document.documentElement.lang = LANGUAGE_META[activeLang].htmlLang;
  siteEyebrow.textContent = uiText("siteEyebrow");
  siteTagline.textContent = uiText("tagline");
  filterLabel.textContent = uiText("filterLabel");
  filterInput.placeholder = uiText("filterPlaceholder");
  sidebarNoteText.textContent = uiText("sidebarNote");
  heroKicker.textContent = uiText("heroKicker").replace("{version}", DOC_STATS.version);
  heroCopy.textContent = uiText("heroCopy");
  navToggle.textContent = uiText("menu");
  toolMetricLabel.textContent = uiText("toolMetric");
  resourceMetricLabel.textContent = uiText("resourceMetric");
  endpointMetricLabel.textContent = uiText("endpointMetric");
  toolMetricValue.textContent = String(DOC_STATS.tools);
  resourceMetricValue.textContent = String(DOC_STATS.resources);
  endpointMetricValue.textContent = String(DOC_STATS.endpoints);
  statusVersion.textContent = `v${DOC_STATS.version}`;
  statusPdf.textContent = uiText("status").pdf;
  statusRagLabel.textContent = uiText("status").ragLabel;
  statusRag.textContent = uiText("status").rag;
  statusKgLabel.textContent = uiText("status").kgLabel;
  statusKg.textContent = uiText("status").kg;
  statusReleaseLabel.textContent = uiText("status").releaseLabel;
  statusRelease.textContent = uiText("status").release;

  quickActionLinks.forEach((link) => {
    const action = link.getAttribute("data-quick-action");
    const label = uiText("quickActions")?.[action];
    if (label) {
      link.textContent = label;
    }
  });
}

function switchLanguage(nextLang) {
  if (!SUPPORTED_LANGUAGES.includes(nextLang) || nextLang === activeLang) {
    return;
  }

  const previousPage =
    pageBySlug(rawSlugFromHash()) || pageBySlug(defaultSlugForLanguage(activeLang));
  activeLang = nextLang;
  persistLanguage(activeLang);
  const nextSlug = translatedSlugFor(previousPage, activeLang);

  if (rawSlugFromHash() === nextSlug) {
    renderPage();
    return;
  }

  window.location.hash = `#/${nextSlug}`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fallbackMarkdown(markdown) {
  return markdown
    .split(/\n{2,}/)
    .map((block) => {
      const trimmed = block.trim();
      if (!trimmed) {
        return "";
      }
      const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        return `<h${level}>${escapeHtml(heading[2])}</h${level}>`;
      }
      return `<p>${escapeHtml(trimmed).replace(/\n/g, "<br>")}</p>`;
    })
    .join("\n");
}

function renderMarkdown(markdown) {
  if (markdownRenderer?.parse) {
    return markdownRenderer.parse(markdown);
  }
  return fallbackMarkdown(markdown);
}

function removeRedundantPageHeading(isOverview) {
  if (isOverview) {
    return;
  }
  const firstElement = docContent.firstElementChild;
  if (firstElement?.tagName === "H1") {
    firstElement.remove();
  }
}

function slugifyHeading(text) {
  return (
    (text || "section")
      .trim()
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-") || "section"
  );
}

function wrapScrollableTables() {
  docContent.querySelectorAll("table").forEach((table) => {
    if (table.parentElement?.classList.contains("table-scroll")) {
      return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    table.replaceWith(wrapper);
    wrapper.appendChild(table);
  });
}

function enhanceDocumentMedia() {
  docContent.querySelectorAll("img").forEach((image) => {
    image.loading = "lazy";
    image.decoding = "async";
  });
}

function buildPageOutline() {
  const headings = Array.from(docContent.querySelectorAll("h2, h3"));
  if (!headings.length) {
    pageOutline.hidden = true;
    pageOutline.innerHTML = "";
    return;
  }

  const seen = new Map();
  const items = headings.map((heading) => {
    const baseId = slugifyHeading(heading.textContent || "section");
    const nextCount = (seen.get(baseId) || 0) + 1;
    seen.set(baseId, nextCount);

    const id = nextCount === 1 ? baseId : `${baseId}-${nextCount}`;
    heading.id = id;
    heading.tabIndex = -1;

    return {
      id,
      level: heading.tagName.toLowerCase(),
      text: heading.textContent?.trim() || "Section",
    };
  });

  pageOutline.hidden = false;
  pageOutline.innerHTML = `
    <div class="outline-panel">
      <p class="outline-title">${escapeHtml(uiText("outlineTitle"))}</p>
      <nav class="outline-nav" aria-label="${escapeHtml(uiText("outlineTitle"))}">
        ${items
          .map(
            (item) => `
              <a class="outline-link ${item.level}" href="#" data-doc-anchor="${escapeHtml(item.id)}">
                ${escapeHtml(item.text)}
              </a>
            `,
          )
          .join("")}
      </nav>
    </div>
  `;
}

async function renderMermaidBlocks() {
  const blocks = Array.from(docContent.querySelectorAll("pre > code.language-mermaid"));
  if (!blocks.length || !window.mermaid) {
    return;
  }

  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {
        fontFamily: '"Segoe UI Variable Text", "Segoe UI", sans-serif',
        primaryColor: "#e9f3f0",
        primaryTextColor: "#172326",
        primaryBorderColor: "#087669",
        lineColor: "#315d5a",
        secondaryColor: "#f7f0df",
        tertiaryColor: "#ffffff",
      },
    });
    mermaidInitialized = true;
  }

  blocks.forEach((block) => {
    const shell = document.createElement("div");
    shell.className = "mermaid-shell";

    const diagram = document.createElement("div");
    diagram.className = "mermaid";
    diagram.textContent = block.textContent || "";

    shell.appendChild(diagram);
    block.parentElement.replaceWith(shell);
  });

  try {
    await mermaid.run({ nodes: Array.from(docContent.querySelectorAll(".mermaid")) });
  } catch (error) {
    console.error("Mermaid rendering failed", error);
  }
}

function wireDocAnchors() {
  pageOutline.querySelectorAll("[data-doc-anchor]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const targetId = link.getAttribute("data-doc-anchor");
      if (!targetId) {
        return;
      }

      const target = docContent.querySelector(`#${CSS.escape(targetId)}`);
      if (!target) {
        return;
      }

      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function searchHaystack(page) {
  const content = embeddedContent[page.slug] || "";
  return [
    page.title,
    page.blurb,
    page.titleByLang?.en,
    page.titleByLang?.zh,
    page.blurbByLang?.en,
    page.blurbByLang?.zh,
    content.replace(/[`#[\]()*_|>-]/g, " "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function pageSearchSnippet(page, normalized) {
  if (!normalized) {
    return pageText(page, "blurb");
  }
  const text = (embeddedContent[page.slug] || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/[`#[\]()*_|>-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const lower = text.toLowerCase();
  const index = lower.indexOf(normalized);
  if (index === -1) {
    return pageText(page, "blurb");
  }
  const start = Math.max(0, index - 42);
  const end = Math.min(text.length, index + normalized.length + 72);
  const prefix = start > 0 ? "..." : "";
  const suffix = end < text.length ? "..." : "";
  return `${prefix}${text.slice(start, end)}${suffix}`;
}

function renderNav(filter = "") {
  const normalized = filter.trim().toLowerCase();
  const active = currentSlug();
  const pages = DOC_PAGES.filter(pageMatchesLanguage).filter((page) => {
    if (!normalized) {
      return true;
    }
    return searchHaystack(page).includes(normalized);
  });

  const resultLabel =
    activeLang === "zh"
      ? `${pages.length} 個結果`
      : `${pages.length} ${pages.length === 1 ? "result" : "results"}`;
  const resultCount = normalized
    ? `<p class="nav-result-count">${escapeHtml(resultLabel)}</p>`
    : "";
  const sections = NAV_GROUPS.map((group) => {
    const groupedPages = pages.filter((page) => page.audience === group);
    if (!groupedPages.length) {
      return "";
    }

    return `
      <section class="nav-section" aria-label="${escapeHtml(UI_COPY[activeLang].groups[group])}">
        <p class="nav-section-title">${escapeHtml(UI_COPY[activeLang].groups[group])}</p>
        ${groupedPages
          .map(
            (page) => `
              <a class="page-link ${page.slug === active ? "active" : ""}" href="#/${page.slug}">
                <strong>${escapeHtml(pageText(page, "title"))}</strong>
                <span>${escapeHtml(pageText(page, "blurb"))}</span>
                ${
                  normalized
                    ? `<span class="page-hit">${escapeHtml(pageSearchSnippet(page, normalized))}</span>`
                    : ""
                }
              </a>
            `,
          )
          .join("")}
      </section>
    `;
  }).join("");

  nav.innerHTML =
    resultCount + (sections || `<p class="nav-empty">${escapeHtml(uiText("noPages"))}</p>`);
}

async function renderPage() {
  const requestedSlug = currentSlug();
  let page = pageBySlug(requestedSlug);

  if (!page) {
    page = pageBySlug(defaultSlugForLanguage(activeLang)) || DOC_PAGES[0];
    if (!page) {
      renderNav(filterInput.value);
      pageOutline.hidden = true;
      return;
    }
    window.location.hash = `#/${page.slug}`;
    return;
  }

  if (page.lang !== "all" && page.lang !== activeLang) {
    activeLang = page.lang;
    persistLanguage(activeLang);
  }

  localizeStaticText();
  renderLanguageControls();
  pageTitle.textContent = pageText(page, "title");
  pageKicker.textContent = pageText(page, "blurb");
  const isOverview = page.group === "overview";
  document.body.classList.toggle("overview-doc-page", isOverview);
  document.body.classList.toggle("compact-doc-page", !isOverview);
  if (summaryBand) {
    summaryBand.hidden = !isOverview;
    summaryBand.setAttribute("aria-hidden", String(!isOverview));
  }
  if (statusStrip) {
    statusStrip.hidden = !isOverview;
    statusStrip.setAttribute("aria-hidden", String(!isOverview));
  }
  renderNav(filterInput.value);

  try {
    const markdown = embeddedContent[page.slug];
    if (!markdown) {
      throw new Error(`Missing embedded content for ${page.slug}.`);
    }

    docContent.innerHTML = renderMarkdown(markdown);
    removeRedundantPageHeading(isOverview);
    wrapScrollableTables();
    enhanceDocumentMedia();
    buildPageOutline();
    wireDocAnchors();
    await renderMermaidBlocks();

    docContent.querySelectorAll("a[href^='http']").forEach((link) => {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noreferrer noopener");
    });

    window.scrollTo(0, 0);
  } catch (error) {
    docContent.innerHTML = `
      <h3>${escapeHtml(uiText("unableTitle"))}</h3>
      <p>${escapeHtml(String(error))}</p>
      <p>${escapeHtml(uiText("regenerate"))}
      <code>python3 scripts/build_docs_site.py</code>
      ${escapeHtml(uiText("regenerateSuffix"))}</p>
    `;
  }
}

filterInput.addEventListener("input", (event) => {
  renderNav(event.target.value);
});

languageControls.forEach((button) => {
  button.addEventListener("click", () => {
    switchLanguage(button.dataset.lang);
  });
});

navToggle.addEventListener("click", () => {
  if (sidebar.classList.contains("open")) {
    closeSidebar();
  } else {
    openSidebar();
  }
});

navClose?.addEventListener("click", closeSidebar);
sidebarBackdrop?.addEventListener("click", closeSidebar);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sidebar.classList.contains("open")) {
    closeSidebar();
    navToggle.focus();
  }
});

window.addEventListener("hashchange", () => {
  closeSidebar();
  renderPage();
});

window.addEventListener("DOMContentLoaded", () => {
  localizeStaticText();
  renderLanguageControls();
  renderNav();
  renderPage();
});
