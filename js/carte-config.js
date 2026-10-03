// js/carte-config.js -- configuration de la carte du site French Place Names.
// Le moteur (commun/carte/carte.js, depot toponymes-commun) lit cet objet :
// il dit quelles expeditions et quelles routes afficher, et construit le
// panneau d'apres `lignes`. Voir commun/README.md.
window.CARTE_CONFIG = {
    panneauAria: "Filtres d'expédition",
    // Jeux de lieux et routes du catalogue commun retenus pour ce site.
    expeditions: { baudin: {}, entre: {} },
    parcours: { baudin: {}, entre: {} },
    // Cartes anciennes proposees dans le selecteur du fond, sur mobile.
    cartesSelecteur: [
        { nom: 'beautemps', libelle: 'Beautemps-Beaupré 1807' },
        { nom: 'freycinet', libelle: 'Freycinet 1808' }
    ],
    // Lettre du fichier des dates remarquables -> couche et case de route.
    remarquables: {
        E: { couche: 'entre', route: 'toggle-entre-parcours' },
        B: { couche: 'baudin', route: 'toggle-baudin-parcours' }
    },
    // Une ligne par expedition : ses lieux, sa route, sa carte ancienne.
    lignes: [
        {
            cle: 'entre', classe: 'toggle-entre', couleur: '#238b45',
            nom: 'd’Entrecasteaux', nomI18n: 'map-layer-entre',
            lieux: { id: 'toggle-entre', coche: true, ariaI18n: 'map-aria-entre-places', aria: "Lieux d'Entrecasteaux" },
            route: { id: 'toggle-entre-parcours', parcours: 'entre', nomFrise: "d'Entrecasteaux",
                     ariaI18n: 'map-aria-entre-route', aria: "Route d'Entrecasteaux" },
            carte: { id: 'toggle-entre-carte', nom: 'beautemps', ariaI18n: 'map-aria-entre-map', aria: 'Carte de Beautemps-Beaupré' },
            navires: { bloc: 'ship-block-entre', liste: 'ship-list-entre', titre: 'Navires' }
        },
        {
            cle: 'baudin', classe: 'toggle-baudin', couleur: '#0b63d1',
            nom: 'Baudin', nomI18n: 'map-layer-baudin',
            lieux: { id: 'toggle-baudin', coche: true, ariaI18n: 'map-aria-baudin-places', aria: 'Lieux Baudin' },
            route: { id: 'toggle-baudin-parcours', parcours: 'baudin', nomFrise: 'Baudin',
                     ariaI18n: 'map-aria-baudin-route', aria: 'Route de Baudin' },
            carte: { id: 'toggle-baudin-carte', nom: 'freycinet', ariaI18n: 'map-aria-baudin-map', aria: 'Carte de Freycinet' },
            navires: { bloc: 'ship-block-baudin', liste: 'ship-list-baudin', titre: 'Navires Baudin' }
        }
    ]
};
