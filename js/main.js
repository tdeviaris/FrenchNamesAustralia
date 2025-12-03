// js/main.js

// Fonction pour marquer le lien de navigation actif
function setActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Mapping des pages vers leurs IDs de navigation
    const pageToNavId = {
        'index.html': 'nav-home',
        'map_dentrecasteaux.html': 'nav-map-dentre',
        'map_baudin.html': 'nav-map-baudin',
        'resources.html': 'nav-resources',
        'glossaryF.html': 'nav-resources',
        'glossaryE.html': 'nav-resources',
        'acteursF.html': 'nav-resources',
        'acteursE.html': 'nav-resources',
        'cartesF.html': 'nav-resources',
        'cartesE.html': 'nav-resources',
        'SourcesF.html': 'nav-resources',
        'SourcesE.html': 'nav-resources',
        'expert.html': 'nav-resources',
        'presentation.html': 'nav-about',
        'author.html': 'nav-about',
        'supporters.html': 'nav-about',
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

document.addEventListener('DOMContentLoaded', () => {
    // Nav déjà inline (injectée au build) : initialiser simplement
    setActiveNavLink();
    initLanguageSwitcher();
    prefetchNavLinks();

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

        // Gestion des pages dédiées par langue (cartes, etc.)
        const pageMap = {
            'cartesF.html': { 'en': 'cartesE.html' },
            'cartesE.html': { 'fr': 'cartesF.html' }
        };
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const redirectTarget = pageMap[currentPage]?.[lang];
        if (redirectTarget && redirectTarget !== currentPage) {
            window.location.href = redirectTarget;
            return;
        }

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

        // Au chargement de la page, vérifie s'il y a une langue sauvegardée, sinon utilise 'en' par défaut
        const savedLang = localStorage.getItem('language') || 'en';
        switchLanguage(savedLang);
    }
});
