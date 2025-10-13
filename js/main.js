// js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const langFrButton = document.getElementById('lang-fr');
    const langEnButton = document.getElementById('lang-en');
    const footerContainer = document.querySelector('[data-include-footer]');

    if (footerContainer) {
        fetch('partials/footer.html')
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

        document.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
            const key = element.getAttribute('data-i18n-aria-label');
            if (key && translations[lang][key]) {
                element.setAttribute('aria-label', translations[lang][key]);
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
});
