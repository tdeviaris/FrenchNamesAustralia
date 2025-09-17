// js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const langFrButton = document.getElementById('lang-fr');
    const langEnButton = document.getElementById('lang-en');

    const switchLanguage = (lang) => {
        // Sauvegarde le choix dans le navigateur
        localStorage.setItem('language', lang);

        // Traduit les éléments de la page en utilisant l'objet du fichier translations.js
        for (const id in translations[lang]) {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = translations[lang][id];
            }
        }

        // Met à jour la langue de la balise <html>
        document.documentElement.lang = lang;

        // Met à jour le style du bouton actif
        langFrButton.classList.toggle('active', lang === 'fr');
        langEnButton.classList.toggle('active', lang === 'en');
        langFrButton.setAttribute('aria-pressed', lang === 'fr');
        langEnButton.setAttribute('aria-pressed', lang === 'en');
    };

    // Ajoute les écouteurs d'événements
    langFrButton.addEventListener('click', () => switchLanguage('fr'));
    langEnButton.addEventListener('click', () => switchLanguage('en'));

    // Au chargement de la page, vérifie s'il y a une langue sauvegardée, sinon utilise 'en' par défaut
    const savedLang = localStorage.getItem('language') || 'en';
    switchLanguage(savedLang);
});
