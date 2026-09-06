// Shared viewer for resource detail sheets and full-size illustrations.
(() => {
  const dialog = document.createElement('dialog');
  dialog.className = 'resource-modal';
  dialog.setAttribute('aria-labelledby', 'resource-modal-title');
  dialog.innerHTML = `<header class="resource-modal-header"><h2 id="resource-modal-title"></h2><button type="button" class="resource-modal-close" aria-label="Fermer">×</button></header><div class="resource-modal-content"></div>`;
  document.body.appendChild(dialog);
  const title = dialog.querySelector('h2');
  const closeButton = dialog.querySelector('button');
  const content = dialog.querySelector('.resource-modal-content');
  let opener;
  const close = () => dialog.close();
  closeButton.addEventListener('click', close);
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close();
  });
  dialog.addEventListener('close', () => {
    content.replaceChildren();
    document.body.classList.remove('resource-modal-open');
    opener?.focus({ preventScroll: true });
  });
  document.addEventListener('languageChanged', () => { if (dialog.open) close(); });
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-resource-modal]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    opener = link;
    const isImage = link.dataset.resourceModal === 'image';
    title.textContent = link.dataset.modalTitle || link.querySelector('img')?.alt || link.textContent.trim();
    closeButton.setAttribute('aria-label', document.documentElement.lang.startsWith('fr') ? 'Fermer' : 'Close');
    const media = document.createElement(isImage ? 'img' : 'iframe');
    media.src = link.href;
    if (isImage) media.alt = title.textContent;
    else {
      media.title = title.textContent;
      media.addEventListener('load', () => {
        // Escape must also close the dialog while focus is inside a detail sheet.
        try {
          media.contentDocument.addEventListener('keydown', event => {
            if (event.key === 'Escape') { event.preventDefault(); close(); }
          });
        } catch { /* External links are opened in separate tabs by the detail sheet. */ }
      });
    }
    dialog.classList.toggle('resource-modal-image', isImage);
    content.replaceChildren(media);
    dialog.showModal();
    document.body.classList.add('resource-modal-open');
    closeButton.focus();
  });
})();
