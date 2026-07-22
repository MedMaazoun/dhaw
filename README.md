# ⚡ Dhaw ضو — Carte des coupures d'électricité en Tunisie

Carte open source, en temps réel, des coupures et délestages STEG au niveau des
**264 délégations** de Tunisie. Née pendant les vagues de chaleur de l'été 2026.

🌐 **Site en ligne : <https://medmaazoun.github.io/dhaw/>**

**3 sources croisées :**

1. 🗓 **Annonces STEG** — un robot (GitHub Actions) lit toutes les 10 minutes les
   flux RSS des médias tunisiens (La Presse, Webdo, Business News, Gnet,
   Tunisie Tribune, L'Économiste Maghrébin) qui relaient les communiqués de la
   STEG, en extrait horaires et localités, et colore les délégations concernées.
2. 📍 **Signalements citoyens** — chaque visiteur peut signaler « coupure » ou
   « courant rétabli » ; partagé en direct via Supabase (expire après 4 h).
3. 🛰 **Satellite NASA VIIRS** — lumières nocturnes réelles (~500 m) des
   7 dernières nuits + référence 2016, pour vérifier visuellement.

Coût d'hébergement : **0 DT / 0 €.** Tout tient sur les offres gratuites.

---

## 🚀 Déployer votre instance en ~10 minutes

### Étape 1 — Le site + le robot (GitHub, gratuit)

1. Créez un compte sur [github.com](https://github.com) si besoin.
2. Créez un dépôt **public** (ex. `dhaw`) → **Add file → Upload files** →
   glissez tout le contenu de ce dossier (y compris le dossier caché
   `.github` — si l'upload web l'ignore, créez le fichier
   `.github/workflows/scrape.yml` à la main en copiant son contenu).
3. **Settings → Pages** → Source : `Deploy from a branch` →
   Branch : `main` / `/ (root)` → Save.
   → Votre carte est en ligne sur `https://VOTRE-PSEUDO.github.io/dhaw/` 🎉
4. Onglet **Actions** → cliquez `I understand… enable workflows` →
   ouvrez `Scraper annonces STEG` → **Run workflow** pour le premier passage.
   Ensuite il tourne tout seul toutes les 10 minutes et committe
   `data/annonces.json`.

> Sans rien d'autre, la carte fonctionne déjà : annonces STEG automatiques
> + satellite. Les signalements citoyens sont en « mode démo local ».

### Étape 2 (optionnelle) — Signalements partagés (Supabase, gratuit)

1. Créez un projet gratuit sur [supabase.com](https://supabase.com).
2. **SQL Editor** → collez le contenu de `supabase/schema.sql` → **Run**.
3. **Settings → API** → copiez `Project URL` et la clé `anon public`.
4. Éditez `config.js` dans votre dépôt GitHub et collez les deux valeurs →
   Commit. C'est tout : les signalements deviennent partagés entre tous les
   visiteurs.

> La clé `anon` est faite pour être publique : la table est protégée par
> Row Level Security (lecture + insertion contrôlée uniquement).
> Pour purger automatiquement les vieux signalements, activez l'extension
> `pg_cron` (instructions en commentaire dans `schema.sql`).

---

## 🗂 Structure

```
├── index.html                  # l'application (Leaflet, aucune build step)
├── config.js                   # URL + clé anon Supabase (optionnel)
├── data/
│   ├── delegations.json        # géométries des 264 délégations (FR + AR)
│   └── annonces.json           # annonces STEG (généré par le robot)
├── scraper/
│   ├── scrape.py               # RSS → horaires + délégations → annonces.json
│   └── requirements.txt
├── supabase/schema.sql         # table reports + politiques RLS
└── .github/workflows/scrape.yml# cron toutes les 10 min
```

## 🔧 Lancer le scraper en local

```bash
pip install -r scraper/requirements.txt
python scraper/scrape.py
```

## 🧭 Feuille de route

- [ ] Scraper direct du site STEG (steg.com.tn) en complément des flux presse
- [ ] PWA installable + notifications push par délégation
- [ ] Historique et statistiques des délestages par gouvernorat
- [ ] Détection automatique de zones sombres sur l'imagerie VIIRS
- [ ] Version arabe complète de l'interface

## ⚠️ Notes & limites honnêtes

- Les annonces dépendent de la précision des communiqués STEG (souvent des
  quartiers ; la carte colore la délégation englobante et affiche la liste
  brute des localités citées).
- L'accès direct à l'API de Facebook/X étant restreint/payant, le robot passe
  par les médias qui relaient chaque communiqué en quelques minutes — même
  contenu, voie légale et stable.
- L'image satellite est prise vers 01h30 du matin ; les nuages assombrissent
  aussi l'image.
- Projet citoyen indépendant, **non affilié à la STEG**. Urgences : 71 239 222.

## 📜 Crédits & licence

Géométries : [riatelab/tunisie](https://github.com/riatelab/tunisie) (INS).
Fonds de carte : © OpenStreetMap / CARTO. Imagerie nocturne : NASA EOSDIS GIBS
(VIIRS Day/Night Band). Licence [MIT](LICENSE).
