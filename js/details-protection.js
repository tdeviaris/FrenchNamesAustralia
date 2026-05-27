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
