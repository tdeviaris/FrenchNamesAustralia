// js/main.js

// Fonction pour marquer le lien de navigation actif
function setActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Mapping des pages vers leurs IDs de navigation
    const pageToNavId = {
        'index.html': 'nav-home',
        'map.html': 'nav-map',
        'resources.html': 'nav-resources',
        'glossary.html': 'nav-resources',
        'actors.html': 'nav-resources',
        'maps.html': 'nav-resources',
        'methodology.html': 'nav-resources',
        'sources.html': 'nav-resources',
        'findings.html': 'nav-resources',
        'findings-1.html': 'nav-resources',
        'findings-2.html': 'nav-resources',
        'findings-3.html': 'nav-resources',
        'findings-4.html': 'nav-resources',
        'findings-5.html': 'nav-resources',
        'findings-6.html': 'nav-resources',
        'illustrations.html': 'nav-resources',
        'rapport.html': 'nav-resources',
        'ships.html': 'nav-resources',
        'expert.html': 'nav-ai',
        'presentation.html': 'nav-about',
        'author.html': 'nav-about',
        'supporters.html': 'nav-about',
        'francois_bellecE.html': 'nav-about',
        'francois_bellecF.html': 'nav-about',
        'teachings.html': 'nav-about',
        'site_map.html': 'nav-about',
        'legal_notice.html': 'nav-about'
    };

    const navId = pageToNavId[currentPage];
    if (navId) {
        const navLink = document.getElementById(navId);
        if (navLink) {
            navLink.classList.add('active');
        }
    }
}

// Prefetch des pages du menu pour réduire le délai perçu
function prefetchNavLinks() {
    const links = document.querySelectorAll('nav a[href]');
    links.forEach((link) => {
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('mailto:')) {
            return;
        }
        // Éviter les doublons
        if (document.querySelector(`link[rel="prefetch"][href="${href}"]`)) {
            return;
        }
        const prefetch = document.createElement('link');
        prefetch.rel = 'prefetch';
        prefetch.href = href;
        prefetch.as = 'document';
        document.head.appendChild(prefetch);
    });
}

function enhanceImagesAvifPreviewThenJpeg() {
    if (!document.getElementById('avif-enhancer-style')) {
        const style = document.createElement('style');
        style.id = 'avif-enhancer-style';
        style.textContent = 'picture[data-avif-enhancer=\"1\"]{display:contents;}';
        document.head.appendChild(style);
    }

    const images = Array.from(document.querySelectorAll('img[src]'));

    images.forEach((img) => {
        if (img.dataset.avifEnhancer === '1') {
            return;
        }

        const srcAttr = img.getAttribute('src');
        if (!srcAttr || !/\.jpe?g(\?.*)?$/i.test(srcAttr)) {
            return;
        }

        // Ne pas toucher aux <img> déjà gérés via <picture> ou <source>
        if (img.closest('picture')) {
            return;
        }

        // Éviter les URLs externes (pas de fichier .avif correspondant garanti)
        if (/^(https?:)?\/\//i.test(srcAttr)) {
            return;
        }

        const avifSrc = srcAttr.replace(/\.jpe?g(\?.*)?$/i, '.avif$1');
        const picture = document.createElement('picture');
        const source = document.createElement('source');

        picture.dataset.avifEnhancer = '1';
        source.type = 'image/avif';
        source.srcset = avifSrc;

        picture.appendChild(source);

        const parent = img.parentNode;
        if (!parent) {
            return;
        }

        parent.insertBefore(picture, img);
        picture.appendChild(img);

        img.dataset.avifEnhancer = '1';
        img.dataset.finalSrc = srcAttr;

        if (!img.hasAttribute('loading')) {
            img.setAttribute('loading', 'lazy');
        }
        if (!img.hasAttribute('decoding')) {
            img.setAttribute('decoding', 'async');
        }

        const shouldUpgradeFromAvif = () => {
            try {
                const current = img.currentSrc || '';
                const url = new URL(current, window.location.href);
                return url.pathname.toLowerCase().endsWith('.avif');
            } catch (e) {
                return (img.currentSrc || '').toLowerCase().includes('.avif');
            }
        };

        const upgradeToJpeg = () => {
            if (!picture.contains(source)) {
                return;
            }
            picture.removeChild(source);
            img.setAttribute('src', img.dataset.finalSrc || srcAttr);
        };

        img.addEventListener('load', () => {
            if (shouldUpgradeFromAvif()) {
                // Laisse le temps d'afficher le preview avant de lancer le chargement du JPEG.
                requestAnimationFrame(() => upgradeToJpeg());
            }
        }, { once: false });

        img.addEventListener('error', () => {
            // Si le .avif n'existe pas/échoue, fallback immédiat vers le JPEG.
            upgradeToJpeg();
        }, { once: true });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Nav déjà inline (injectée au build) : initialiser simplement
    setActiveNavLink();
    initLanguageSwitcher();
    prefetchNavLinks();
    enhanceImagesAvifPreviewThenJpeg();

    const footerContainer = document.querySelector('[data-include-footer]');

    if (footerContainer) {
        // Chemin footer compatible GitHub Pages (sous-répertoire) et Vercel (racine)
        const footerPath = window.location.hostname.includes('github.io')
            ? '/FrenchNamesAustralia/partials/footer.html'
            : '/partials/footer.html';

        fetch(footerPath)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.text();
            })
            .then(html => {
                footerContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('Failed to load footer:', error);
            });
    }

    function initLanguageSwitcher() {
        const langFrButton = document.getElementById('lang-fr');
        const langEnButton = document.getElementById('lang-en');

        if (!langFrButton || !langEnButton) {
            console.warn('Language switcher buttons not found');
            return;
        }

        const switchLanguage = (lang) => {
            // Sauvegarde le choix dans le navigateur
            localStorage.setItem('language', lang);

        // Traduit les éléments de la page en utilisant l'objet du fichier translations.js
        // D'abord par ID (ancien système)
        for (const id in translations[lang]) {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = translations[lang][id];
            }
        }

        // Puis par data-i18n (nouveau système)
        document.querySelectorAll('[data-i18n]').forEach((element) => {
            const key = element.getAttribute('data-i18n');
            if (key && translations[lang][key]) {
                element.innerHTML = translations[lang][key];
            }
        });

        // Gestion des éléments avec data-i18n-html
        document.querySelectorAll('[data-i18n-html]').forEach((element) => {
            const key = element.getAttribute('data-i18n-html');
            if (key && translations[lang][key]) {
                element.innerHTML = translations[lang][key];
            }
        });

        document.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
            const key = element.getAttribute('data-i18n-aria-label');
            if (key && translations[lang][key]) {
                element.setAttribute('aria-label', translations[lang][key]);
            }
        });

        // Gestion des sources audio/vidéo avec data-i18n-src
        document.querySelectorAll('[data-i18n-src]').forEach((element) => {
            const key = element.getAttribute('data-i18n-src');
            if (key && translations[lang][key]) {
                const source = element.querySelector('source');
                if (source) {
                    source.setAttribute('src', translations[lang][key]);
                    element.load(); // Recharge l'élément audio/vidéo avec la nouvelle source
                }
            }
        });

        // Met à jour la langue de la balise <html>
        document.documentElement.lang = lang;

        // Met à jour le style du bouton actif
        langFrButton.classList.toggle('active', lang === 'fr');
        langEnButton.classList.toggle('active', lang === 'en');
        langFrButton.setAttribute('aria-pressed', lang === 'fr');
        langEnButton.setAttribute('aria-pressed', lang === 'en');

        // Déclenche un événement personnalisé pour que d'autres scripts puissent réagir
        document.dispatchEvent(new Event('languageChanged'));
        };

        // Ajoute les écouteurs d'événements
        langFrButton.addEventListener('click', () => switchLanguage('fr'));
        langEnButton.addEventListener('click', () => switchLanguage('en'));

        // Au chargement, détermine la langue initiale.
        const getInitialLanguage = () => {
            // Priorité 1: Langue déjà sauvegardée par l'utilisateur.
            const savedLang = localStorage.getItem('language');
            if (savedLang) {
                return savedLang;
            }
            // Priorité 2: Détection de la langue du navigateur.
            const browserLang = navigator.language || navigator.userLanguage;
            return browserLang.startsWith('fr') ? 'fr' : 'en';
        };

        switchLanguage(getInitialLanguage());
    }
});
