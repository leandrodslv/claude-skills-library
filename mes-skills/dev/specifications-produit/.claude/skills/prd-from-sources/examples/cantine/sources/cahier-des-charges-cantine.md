# Cahier des charges — Application « Cantine »

## 1. Contexte
École primaire des Tilleuls, 212 élèves, 180 demi-pensionnaires en moyenne. Service de restauration du lundi au vendredi.

## 2. Utilisateurs
- **Parent** : réserve, modifie et annule les repas de ses enfants.
- **Agent de cantine** : consulte la liste des repas du jour et de la semaine.
- **Agent de mairie** : reçoit la liste hebdomadaire de commande.

## 3. Fonctions attendues
3.1 Le parent peut réserver un repas pour un jour donné et pour chacun de ses enfants.
3.2 Le parent peut annuler une réservation jusqu'à 48 h avant le repas.
3.3 L'agent de cantine voit, pour chaque jour, le nombre de repas et la liste des allergies signalées.
3.4 Le système envoie à la mairie, le jeudi à 12 h, le récapitulatif des repas de la semaine suivante.
3.5 Le parent reçoit un rappel la veille de la fin des réservations.

## 4. Contraintes
- Disponibilité : l'application doit fonctionner le jeudi matin, jour de commande.
- Données d'enfants : conformité RGPD, hébergement en France.
- Accessibilité : application utilisable par des parents peu à l'aise avec le numérique (RGAA).
- Temps de réponse : une réservation doit s'enregistrer en moins de 3 secondes.
