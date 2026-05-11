/* global marked, mermaid */

const DOC_PAGES = window.ASSET_AWARE_DOC_PAGES || [];
const embeddedContent = window.ASSET_AWARE_DOC_PAGE_CONTENT || {};
const LANGUAGE_STORAGE_KEY = "asset-aware-docs-language";
const SUPPORTED_LANGUAGES = ["en", "zh"];
const LANGUAGE_META = {
  en: { htmlLang: "en", label: "EN" },
  zh: { htmlLang: "zh-TW", label: "繁中" },
};
const NAV_GROUPS = ["start", "user", "developer", "reference"];
const UI_COPY = {
  en: {
    siteEyebrow: "Documentation Site",
    tagline: "Citation-ready document workflows for AI agents.",
    filterLabel: "Filter pages",
    filterPlaceholder: "PDF, DOCX, citation, VSIX...",
    sidebarNote:
      "Content is generated from docs/wiki. The GitHub Wiki and Pages site share the same functionality source.",
    heroKicker: "Complete docs site",
    heroCopy:
      "A workflow-oriented handbook for Asset-Aware MCP: user flows, developer architecture, MCP tools and resources, citation provenance, VSIX setup, and release checks.",
    menu: "Menu",
    outlineTitle: "On This Page",
    noPages: "No pages match this filter.",
    unableTitle: "Unable to load page",
    regenerate: "Run",
    regenerateSuffix: "to regenerate site content.",
    toolMetric: "MCP tools",
    resourceMetric: "MCP resources",
    endpointMetric: "endpoints",
    groups: {
      start: "Start Here",
      user: "Workflows",
      developer: "For Developers",
      reference: "Reference",
    },
  },
  zh: {
    siteEyebrow: "文件網站",
    tagline: "給 AI agents 使用的 citation-ready 文件工作流。",
    filterLabel: "篩選頁面",
    filterPlaceholder: "PDF、DOCX、citation、VSIX...",
    sidebarNote:
      "文件內容由 docs/wiki 生成；GitHub Wiki 與 Pages site 共用同一份功能說明來源。",
    heroKicker: "完整文件網站",
    heroCopy:
      "以角色與工作流整理 Asset-Aware MCP：使用者流程、開發者架構、MCP tools/resources、citation provenance、VSIX 設定與 release checks。",
    menu: "選單",
    outlineTitle: "本頁內容",
    noPages: "沒有符合篩選條件的頁面。",
    unableTitle: "無法載入頁面",
    regenerate: "請執行",
    regenerateSuffix: "重新生成 site content。",
    toolMetric: "MCP tools",
    resourceMetric: "MCP resources",
    endpointMetric: "endpoints",
    groups: {
      start: "開始",
      user: "工作流",
      developer: "開發者",
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
const sidebar = document.getElementById("sidebar");
const siteEyebrow = document.getElementById("site-eyebrow");
const siteTagline = document.getElementById("site-tagline");
const sidebarNoteText = document.getElementById("sidebar-note-text");
const heroKicker = document.getElementById("hero-kicker");
const heroCopy = document.getElementById("hero-copy");
const toolMetricLabel = document.getElementById("tool-metric-label");
const resourceMetricLabel = document.getElementById("resource-metric-label");
const endpointMetricLabel = document.getElementById("endpoint-metric-label");
const languageControls = Array.from(document.querySelectorAll("[data-lang]"));
let mermaidInitialized = false;
let activeLang = preferredLanguage();

marked.setOptions({
  gfm: true,
  breaks: false,
});

function preferredLanguage() {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (SUPPORTED_LANGUAGES.includes(stored)) {
      return stored;
    }
  } catch (_error) {
    // Storage can be blocked in local or privacy-constrained contexts.
  }

  const browserLanguage = (window.navigator.language || "").toLowerCase();
  return browserLanguage.startsWith("zh") ? "zh" : "en";
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
  navToggle.setAttribute("aria-expanded", "false");
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
  heroKicker.textContent = uiText("heroKicker");
  heroCopy.textContent = uiText("heroCopy");
  navToggle.textContent = uiText("menu");
  toolMetricLabel.textContent = uiText("toolMetric");
  resourceMetricLabel.textContent = uiText("resourceMetric");
  endpointMetricLabel.textContent = uiText("endpointMetric");
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
  return [
    page.title,
    page.blurb,
    page.titleByLang?.en,
    page.titleByLang?.zh,
    page.blurbByLang?.en,
    page.blurbByLang?.zh,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
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
              </a>
            `,
          )
          .join("")}
      </section>
    `;
  }).join("");

  nav.innerHTML = sections || `<p class="nav-empty">${escapeHtml(uiText("noPages"))}</p>`;
}

async function renderPage() {
  const requestedSlug = currentSlug();
  let page = pageBySlug(requestedSlug);

  if (!page) {
    page = pageBySlug(defaultSlugForLanguage(activeLang)) || DOC_PAGES[0];
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
  renderNav(filterInput.value);

  try {
    const markdown = embeddedContent[page.slug];
    if (!markdown) {
      throw new Error(`Missing embedded content for ${page.slug}.`);
    }

    docContent.innerHTML = marked.parse(markdown);
    wrapScrollableTables();
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
  const isOpen = sidebar.classList.toggle("open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
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
