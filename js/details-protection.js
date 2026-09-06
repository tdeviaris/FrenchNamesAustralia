(function () {
  if (window.__detailsProtectionInstalled) {
    return;
  }
  window.__detailsProtectionInstalled = true;

  const root = document.documentElement;
  if (root) {
    root.dataset.detailsProtectionInstalled = "true";
  }

  const style = document.createElement("style");
  style.textContent = [
    "html, body {",
    "  -webkit-touch-callout: none;",
    "  -webkit-user-select: none;",
    "  -moz-user-select: none;",
    "  -ms-user-select: none;",
    "  user-select: none;",
    "}",
    "img {",
    "  -webkit-user-drag: none;",
    "  user-drag: none;",
    "}"
  ].join("\n");
  document.head.appendChild(style);

  // Detail sheets are displayed in an iframe. External sources must open
  // outside it, since many archives and libraries refuse to be embedded.
  const prepareExternalLinks = () => {
    const isFrench = /^fr\b/i.test(root.lang) ||
      (!root.lang && /F\.html$/i.test(window.location.pathname));
    const notice = document.createElement("span");
    notice.id = "details-new-tab-notice";
    notice.textContent = isFrench ? "S’ouvre dans un nouvel onglet" : "Opens in a new tab";
    notice.hidden = true;
    document.body.appendChild(notice);

    document.querySelectorAll("a[href]").forEach((link) => {
      let url;
      try {
        url = new URL(link.getAttribute("href"), document.baseURI);
      } catch {
        return;
      }
      if (!["http:", "https:"].includes(url.protocol) || url.origin === window.location.origin) {
        return;
      }
      link.target = "_blank";
      link.relList.add("noopener", "noreferrer");
      const descriptions = new Set((link.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean));
      descriptions.add(notice.id);
      link.setAttribute("aria-describedby", [...descriptions].join(" "));
      link.title = link.title ? `${link.title} — ${notice.textContent}` : notice.textContent;
      const indicator = document.createElement("span");
      indicator.textContent = " ↗";
      indicator.setAttribute("aria-hidden", "true");
      link.appendChild(indicator);
    });
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", prepareExternalLinks, { once: true });
  } else {
    prepareExternalLinks();
  }

  const shouldAllowEditableTarget = (target) => {
    if (!(target instanceof Element)) {
      return false;
    }
    return Boolean(target.closest("input, textarea, [contenteditable='true']"));
  };

  const preventAction = (event) => {
    if (shouldAllowEditableTarget(event.target)) {
      return;
    }
    event.preventDefault();
  };

  document.addEventListener("copy", preventAction, true);
  document.addEventListener("cut", preventAction, true);
  document.addEventListener("paste", preventAction, true);
  document.addEventListener("selectstart", preventAction, true);
  document.addEventListener("dragstart", preventAction, true);
  document.addEventListener("contextmenu", (event) => {
    if (event.target instanceof HTMLImageElement) {
      event.preventDefault();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if (shouldAllowEditableTarget(event.target)) {
      return;
    }
    if ((event.ctrlKey || event.metaKey) && ["a", "c", "x", "v"].includes(event.key.toLowerCase())) {
      event.preventDefault();
    }
  }, true);

  document.addEventListener("selectionchange", () => {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
      selection.removeAllRanges();
    }
  }, true);
})();
