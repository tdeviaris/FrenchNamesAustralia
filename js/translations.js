// js/translations.js
const translations = {
    'fr': {
        // --- Textes généraux ---
        'hero-title': "Noms Français le long de la côte Australienne", 'hero-subtitle': "Les toponymes issus des voyages de d’Entrecasteaux (1791-1794) et Baudin (1800-1804)",
        'nav-home': "Accueil", 'nav-map-dentre': "Carte Interactive : d'Entrecasteaux", 'nav-map-baudin': "Carte Interactive : Baudin", 'nav-resources': "Ressources",
        'footer-text': '&copy; 2024 - Dany Bréelle - Projet "Noms Français le long de la côte Australienne"',

        // --- Page d'accueil (index.html) ---
        'intro-title': "Introduction", 'intro-p1': "Ce projet explore l'héritage distinctif de la toponymie française...", 'intro-p2': "En se concentrant sur les plus de 670 sites nommés...", 'intro-p3': "<em>La recherche présentée sur ce site a été soutenue par la RGSSA, la WAHF, …</em>",
        'map-title-freycinet': "Carte de Freycinet, 1812", 'map-title-beautemps': "Carte de Beautemps-Beaupré, 1807",

        // --- Page Carte d'Entrecasteaux ---
        'dentre-title': "Carte Interactive : L'Expédition d'Entrecasteaux (1791-1793)", 'dentre-desc': "Explorez les noms de lieux donnés lors de l'expédition d'Antoine Bruny d'Entrecasteaux...",
        'dentre-text-p1': "Le premier objectif de l'expédition d'Entrecasteaux...", 'dentre-text-p2': "Les côtes est de la Terre de Van Diemen (Tasmanie)...", 'dentre-text-p3': "68 lieux furent nommés le long de ces côtes...", 'dentre-text-p4': "Ce ne fut pas une tâche facile pour le commandant...", 'dentre-text-p5': "Des officiers, comme Jurien...", 'dentre-text-p6': "Les lieux visités et nommés par l'expédition...",
        
        // --- Page Carte Baudin ---
        'baudin-title': "Carte Interactive : L'Expédition de Nicolas Baudin (1800-1804)", 'baudin-desc': "Explorez les noms de lieux donnés lors de l'expédition scientifique de Nicolas Baudin...", 'map-title-baudin': "Carte de Baudin, 1802",

        // --- Page Ressources ---
        'resources-title': "Ressources", 'resources-p1': "Cette page contiendra des ressources additionnelles...", 'resources-p2': "<em>(Contenu à ajouter)</em>",

        // --- Page de détail Baie de la Recherche ---
        'detail-rb-title': "Baie de la Recherche / Recherche Bay",
        'detail-rb-fig-caption': "Fig.1. Baie de la Recherche, section de la carte ‘Carte particulière du Canal Dentrecasteaux, entre la terre méridionale d'Anthony Van Diemen et l'île Bruny…’, Par Beautemps-Beaupré, Charles François, in Atlas du voyage de Bruny d’Entrecasteaux... 1807, Planche 4. Bibliothèque Nationale d'Australie.",
        'detail-rb-fig-link': "https://nla.gov.au/nla.obj-230810562/view",
        'detail-rb-fig-legend': "Les tracés des navires et des canots ont été colorés différemment pour distinguer les campagnes hydrographiques de 1792 (bleu et rouge) de celles de 1793 (violet et vert).",
        'detail-rb-legend-north': "Nord",
        'detail-rb-legend-vessels1792': "Tracé des navires la Recherche et l’Espérance en 1792",
        'detail-rb-legend-longboats1792': "Tracé des canots en 1792",
        'detail-rb-legend-vessels1793': "Tracé des navires la Recherche et l’Espérance en 1793",
        'detail-rb-legend-longboats1793': "Tracé des canots en 1793",
        'detail-rb-heading1': "L'arrivée tumultueuse des frégates sur les côtes sud-est de la Tasmanie",
        'detail-rb-p1': "Les frégates atteignirent Ténériffe le 23 octobre, et le Cap de Bonne-Espérance le 16 février 1792. Initialement, l'expédition mit le cap sur les îles de l'Amirauté (au nord de la Nouvelle-Guinée) à la recherche d'informations sur l'expédition de La Pérouse, car des rumeurs au Cap suggéraient que des habitants de ces îles avaient été vus portant des uniformes et des accessoires navals français qui auraient pu provenir de l'expédition perdue. Le départ du Cap marqua le début de la mission officielle du voyage, commençant par le relevé des îles d'Amsterdam et de Saint-Paul (océan Indien). Les instructions de d'Entrecasteaux étaient de relever ensuite la côte sud-ouest de la Nouvelle-Hollande, avant d'atteindre la Nouvelle-Guinée[1]. Cependant, la force des vents d'ouest soufflant sans interruption pendant plusieurs semaines[2] et la mer extrêmement grosse mettaient 'les frégates à rude épreuve' et 'entraînaient des ruptures de chaînes' tandis que 'l'eau a pénétré dans les soutes des navires…'[3]. Dans ces circonstances et avec l'hiver imminent, le commandant, qui avait fait une mauvaise chute lors d'un violent roulis et s'était gravement blessé aux côtes (mars-début avril 1792), modifia pragmatiquement son itinéraire et se dirigea vers les côtes mieux protégées de l'est de la Tasmanie, alors connue sous le nom de Terre de Van Diemen (voir le glossaire).",
        'detail-rb-p2': "La côte sud-est de la Tasmanie fut aperçue pour la première fois le 20 avril 1792, et l'expédition entra le 23 avril 1792 dans une baie abritée (Baie de la Recherche*) où les frégates jetèrent l'ancre et furent réparées. Les maillons brisés entre la chaîne et le câble de l'ancre de <em>la Recherche</em>, qui 'avaient probablement été surchauffés par le métallurgiste qui l'avait forgée', furent réparés[4].",
        'detail-rb-heading2': "La dénomination du canal d’Entrecasteaux",
        'detail-rb-p3': "Pendant leur séjour, les hydrographes et les officiers préparèrent les premières cartes des côtes bordant le Canal d'Entrecasteaux* et nommèrent de nombreux lieux. Après leur départ le 28 mai, ils contournèrent l'Australie par une route lointaine via la Nouvelle-Calédonie, les îles Salomon, la Nouvelle-Irlande, l'île de l'Amirauté, Amboine, le Cap Leeuwin et la côte sud-ouest de la Nouvelle-Hollande, avant de retourner en Terre de Van Diemen pour cinq semaines, du 21 janvier au 27 février 1793, afin de compléter leur reconnaissance.",
        'detail-rb-p4': "Le long des rives de la Terre de Van Diemen, le commandant nomma certaines caractéristiques géographiques d'après les membres de son équipage qui avaient le plus contribué aux résultats des levés, surtout après que les canots de l'expédition eurent été envoyés pour cartographier les côtes rocheuses du canal, leurs baies et étudier leur histoire naturelle[5]. Finalement, 50 lieux de la Terre de Van Diemen reçurent un nom. Plus de la moitié de ces noms sont liés aux deux frégates de l'expédition, <em>la Recherche</em> et <em>l'Espérance</em> (Baie de la Recherche*, Port de l’Espérance*, etc.) et aux membres de l'équipage de l'expédition (23)[6]. 16 autres noms sont basés sur des emplacements géographiques (<em>Port du Nord Ouest</em>*…) et sur la géographie physique des côtes (<em>Baie de l'Isthme</em>*…). 5 autres noms évoquent la faune et la flore locales (Port des cygnes*…), et un nom fait référence à l'explorateur français Marion Dufresne dont les navires passèrent plusieurs jours dans la baie de Marion en Terre de Van Diemen en mars 1772.",
        'detail-rb-p5': "Ces trois cartes ci-dessous montrent des parties des côtes de la Terre de Van Diemen visitées par l'expédition. Elles sont extraites de la première édition (1807) de l'atlas du voyage de d'Entrecasteaux et indiquent l'emplacement des lieux qu'il avait nommés[7]. Elles ont été modifiées pour indiquer et distinguer par des couleurs les tracés de 1792 (en bleu) et 1793 (en violet) des navires et de leurs équipes de relevé (en 1792, en rouge, principalement dans la partie sud, et plus tard, en 1793, en vert, surtout au nord du Canal). Les méandres des tracés sur ces cartes suggèrent les difficultés rencontrées par les arpenteurs pour approcher et explorer le littoral, ce que les noms donnés à certains lieux expriment parfois, comme le '<em>Cap des Contrariétés</em>'*.",
        
        // --- Étiquettes pour les fiches des cartes (Popups) ---
        'popup-french-name': "Nom français :", 'popup-ause-name': "Nom AusE :", 'popup-indigenous-name': "En", 'popup-coordinates': "Coordonnées :", 'popup-characteristic': "Caractéristique :", 'popup-details-link': "Pour un compte-rendu détaillé et les références, cliquez ici."
    },
    'en': {
        // --- General text ---
        'hero-title': "French Names Along the Australian Coastline", 'hero-subtitle': "The toponyms originated by the d’Entrecasteaux (1791-1794) and Baudin (1800-1804) voyages",
        'nav-home': "Home", 'nav-map-dentre': "Interactive Map: d'Entrecasteaux", 'nav-map-baudin': "Interactive Map: Baudin", 'nav-resources': "Resources",
        'footer-text': '&copy; 2024 - Dany Bréelle - "French Names Along the Australian Coastline" Project',

        // --- Homepage (index.html) ---
        'intro-title': "Introduction", 'intro-p1': "This project explores the distinctive legacy of French place naming...", 'intro-p2': "By focusing on the over 670 sites named...", 'intro-p3': "<em>The research in this website was supported by the RGSSA, the WAHF, …</em>",
        'map-title-freycinet': "Map by Freycinet, 1812", 'map-title-beautemps': "Map by Beautemps-Beaupré, 1807",

        // --- d'Entrecasteaux Map Page ---
        'dentre-title': "Interactive Map: The d'Entrecasteaux Expedition (1791-1793)", 'dentre-desc': "Explore the place names given during the expedition of Antoine Bruny d'Entrecasteaux...",
        'dentre-text-p1': "The first object of the d’Entrecastreaux expedition...", 'dentre-text-p2': "The east coasts of Van Diemen Land (Tasmania)...", 'dentre-text-p3': "68 places were named along these coasts...", 'dentre-text-p4': "It had not been an easy task for the commander...", 'dentre-text-p5': "Officers, such as Jurien...", 'dentre-text-p6': "The places visited and named by the d’Entrecasteaux expedition...",
        
        // --- Baudin Map Page ---
        'baudin-title': "Interactive Map: The Nicolas Baudin Expedition (1800-1804)", 'baudin-desc': "Explore the place names given during the scientific expedition of Nicolas Baudin...", 'map-title-baudin': "Map from Baudin expedition, 1802",

        // --- Resources Page ---
        'resources-title': "Resources", 'resources-p1': "This page will contain additional resources...", 'resources-p2': "<em>(Content to be added)</em>",
        
        // --- Detail Page Recherche Bay ---
        'detail-rb-title': "Baie de la Recherche / Recherche Bay",
        'detail-rb-fig-caption': "Fig.1. Recherche Bay, section of the map ‘Carte particulière du Canal Dentrecasteaux, entre la terre méridionale d'Anthony Van Diemen et l'île Bruny…’, By Beautemps-Beaupré, Charles François, in Atlas du voyage de Bruny d’Entrecasteaux... 1807, Plate 4. National Library of Australia.",
        'detail-rb-fig-link': "https://nla.gov.au/nla.obj-230810562/view",
        'detail-rb-fig-legend': "The tracks of the vessels and boats have been colored differently to distinguish the hydrographic campaigns of 1792 (blue and red) from those of 1793 (purple and green).",
        'detail-rb-legend-north': "North",
        'detail-rb-legend-vessels1792': "track of la Recherche and l’Espérance’ vessels in 1792",
        'detail-rb-legend-longboats1792': "track of the longboats in 1792",
        'detail-rb-legend-vessels1793': "track of la Recherche and l’Espérance’ vessels in 1793",
        'detail-rb-legend-longboats1793': "track of the longboats in 1793",
        'detail-rb-heading1': "The frigates’ blustery arrival on the South-Eastern Tasmanian coasts",
        'detail-rb-p1': "The frigates reached Teneriffe on 23 October, and the Cape of Good Hope on 16 February 1792. Initially, it then set sail for the Admiralties islands (to the North of New Guinea) in search for information about the La Pérouse expedition, as there had been rumours in Cape Town that some inhabitants of these islands were seen wearing French uniforms and naval accessories that might have come from the lost expedition. The departure from the Cape was the start of the voyage official mission, beginning with the survey of the islands of Amsterdam and St Paul (Indian Ocean). d’Entrecasteaux’s instructions were to then survey the southwest coast of New Holland, before reaching New Guinea[1]. However, the strength of the westerlies blowing without interruption for some weeks[2] and the extremely heavy seas were ‘a strain on the frigates’ and ‘resulted in broken chains’ while ‘water has penetrated the vessels into the storerooms…’[3]. Under these circumstances and with the winter season imminent, the commander, who had a bad fall when the ship rolled violently and severely injured his ribs (March-beginning of April 1792), pragmatically changed his itinerary, and headed for the better protected East coasts of Tasmania, then known as Van Diemen Land (see the glossary).",
        'detail-rb-p2': "The southeastern Tasmanian coast was first sighted on 20 April 1792, and the expedition entered on 23 April 1792 in a sheltered bay (Recherche Bay*) where the frigates anchored and were repaired. The broken links between the chain and the cable of the anchor of <em>la Recherche</em> which ‘had probably been overheated by the metalworker who had forged it’ were fixed[4].",
        'detail-rb-heading2': "The naming of the d’Entrecasteaux channel",
        'detail-rb-p3': "During their stay, the hydrographers and officers prepared the first charts of the coasts bordering the d’Entrecasteaux Channel* and gave names to many of its places. Following their departure on 28 May, they circumnavigated Australia by a remote route via New Caledonia, Salomon Islands, New-Ireland, the Admiralty Island, Amboina, Cap Leuwin, and the southwest coast of New-Holland, before returning to Van Diemen Land for five weeks, from 21 January to 27 February 1793, to complete their reconnaissance.",
        'detail-rb-p4': "Along the shores of Van Diemen Land, the commander named some geographical features after members of his crew who had contributed most to the surveys’ results, especially after the expedition’s dinghies had been dispatched to chart the channel’s rocky coasts, their bays and to study their natural history[5]. Ultimately, 50 places in Van Diemen Land’s places received a name. More than half of these names are linked to the expedition’s two frigates, <em>la Recherche</em> and <em>l'Espérance</em> (Baie de la Recherche*, Port de l’Espérance* etc) and to members of his expedition’s crew (23)[6]. Another 16 names are based on geographical locations (<em>Port du Nord Ouest</em>*…) and on the physical geography of the coasts (<em>Baie de l'Isthme</em>*…). A further 5 names evoke the local fauna and flora (Port des cygnes*…), and one name refers to the French explorer Marion Dufresne whose ships spent several days in Marion Bay in Van Diemen Land in March 1772.",
        'detail-rb-p5': "These three charts below show parts of the coasts of Van Diemen’s Land visited by the expedition. They are extract from the first edition (1807) of the atlas of d’Entrecasteaux voyage and mark the location of the places he had named[7]. They have been altered to indicate and distinguish with colors the 1792 (in blue) and 1793 (in purple) tracks of the vessels and of their surveying parties (in 1792, in red, mainly in the south part, and later, in 1793, in green, especially in the north of the Canal). The twists and turns of the tracks plotted on these charts suggest the difficulties faced by the surveyors in approaching and exploring the coastline, which names given to some places occasionally express, such as ‘<em>Cap des Contrariétés</em>’*.",

        // --- Labels for Map Popups ---
        'popup-french-name': "French name:", 'popup-ause-name': "AusE name:", 'popup-indigenous-name': "In", 'popup-coordinates': "Coordinates:", 'popup-characteristic': "Characteristic:", 'popup-details-link': "For a detailed account and references, click here."
    }
};
