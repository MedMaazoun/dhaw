// ── Configuration Dhaw ─────────────────────────────────────────────
// Sans Supabase, la carte fonctionne (annonces STEG + satellite),
// mais les signalements citoyens restent en mode démo local.
// Pour les activer : créez un projet gratuit sur supabase.com,
// exécutez supabase/schema.sql, puis renseignez ces deux valeurs
// (Settings → API → Project URL / anon public key).
window.DHAW_CONFIG = {
  SUPABASE_URL: "",        // ex: "https://xxxx.supabase.co"
  SUPABASE_ANON_KEY: ""    // ex: "eyJhbGciOi..."
};
