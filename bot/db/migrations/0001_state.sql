-- Schéma initial : état propre à chaque bot (bot_*) et état / données du
-- calcul (compute_*). Commentaires uniquement sur des lignes entières
-- (cf. bot/db/migrate.py).

-- ── État propre à chaque bot ──────────────────────────────────────────
-- bot_id distingue deux bots (live / lite) partageant la même base.

-- Abonnements /botconfig : un salon (ou thread) par topic et par serveur.
CREATE TABLE IF NOT EXISTS bot_subscription (
  bot_id       VARCHAR(16)     NOT NULL,
  guild_id     BIGINT UNSIGNED NOT NULL,
  topic        VARCHAR(48)     NOT NULL,
  channel_id   BIGINT UNSIGNED NOT NULL,
  is_thread    TINYINT(1)      NOT NULL DEFAULT 0,
  role_id      BIGINT UNSIGNED NULL,
  guild_name   VARCHAR(100)    NULL COMMENT 'debug uniquement',
  channel_name VARCHAR(100)    NULL COMMENT 'debug uniquement',
  PRIMARY KEY (bot_id, guild_id, topic, channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ce que ce bot a publié pour un topic dans un serveur.
-- content_hash vide ou NULL = à republier (refresh, envoi partiel).
CREATE TABLE IF NOT EXISTS bot_publication (
  bot_id       VARCHAR(16)     NOT NULL,
  guild_id     BIGINT UNSIGNED NOT NULL,
  topic        VARCHAR(48)     NOT NULL,
  version      INT UNSIGNED    NULL COMMENT 'version de content_post publiée',
  content_hash VARCHAR(64)     NULL,
  updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (bot_id, guild_id, topic)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- IDs des messages Discord publiés, dans leur ordre d'envoi.
-- slot : 'content' (messages de contenu + ping), 'status' (statut Xûr).
CREATE TABLE IF NOT EXISTS bot_message (
  bot_id     VARCHAR(16)       NOT NULL,
  guild_id   BIGINT UNSIGNED   NOT NULL,
  topic      VARCHAR(48)       NOT NULL,
  slot       VARCHAR(16)       NOT NULL,
  position   SMALLINT UNSIGNED NOT NULL,
  message_id BIGINT UNSIGNED   NOT NULL,
  PRIMARY KEY (bot_id, guild_id, topic, slot, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── État du calcul ────────────────────────────────────────────────────

-- Petites valeurs nommées, encodées en JSON : dernier reset traité,
-- signatures de fraîcheur, défis de la semaine, anti-doublons news et
-- maintenance, tokens OAuth Bungie.
CREATE TABLE IF NOT EXISTS compute_state (
  name       VARCHAR(96) NOT NULL PRIMARY KEY,
  value      MEDIUMTEXT  NOT NULL,
  updated_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Données éditées à la main (phpMyAdmin) ────────────────────────────
-- Relues par le bot toutes les 10 minutes.

-- Tables de butin (/loottable) : une ligne par activité ...
CREATE TABLE IF NOT EXISTS compute_loot_table (
  activity_key VARCHAR(48)       NOT NULL PRIMARY KEY,
  label        VARCHAR(100)      NOT NULL,
  banner_file  VARCHAR(128)      NULL COMMENT 'fichier dans Ressources/ActivityBanner',
  type         VARCHAR(32)       NULL COMMENT 'prestige / destination',
  sort_order   SMALLINT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ... et une ligne par item, dans l'ordre d'affichage.
CREATE TABLE IF NOT EXISTS compute_loot_table_item (
  activity_key VARCHAR(48)       NOT NULL,
  position     SMALLINT UNSIGNED NOT NULL,
  item_hash    INT UNSIGNED      NOT NULL,
  PRIMARY KEY (activity_key, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vœux du Wishwall, dans l'ordre du menu.
CREATE TABLE IF NOT EXISTS compute_wish (
  position     SMALLINT UNSIGNED NOT NULL PRIMARY KEY,
  name         VARCHAR(150)      NOT NULL,
  description  TEXT              NOT NULL,
  image_file   VARCHAR(128)      NULL COMMENT 'fichier dans Ressources/RivenWishes',
  button_label VARCHAR(100)      NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Boucliers et champions des secteurs oubliés, par activité.
CREATE TABLE IF NOT EXISTS compute_lost_sector_extra (
  activity_hash INT UNSIGNED                  NOT NULL,
  kind          ENUM('shields', 'champions')  NOT NULL,
  name          VARCHAR(64)                   NOT NULL COMMENT 'ex. Solaires, Perturbation',
  count         SMALLINT UNSIGNED             NOT NULL,
  position      SMALLINT UNSIGNED             NOT NULL DEFAULT 0,
  PRIMARY KEY (activity_hash, kind, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Activités toujours disponibles (raids / donjons « permanents »).
CREATE TABLE IF NOT EXISTS compute_permanent_activity (
  activity_hash INT UNSIGNED NOT NULL PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Positions (1 = premier emplacement du vendeur) gardées par catégorie Xûr.
-- positions : liste séparée par des virgules, ex. '2,3,4'. Vide = aucune.
-- Catégorie absente de la table = tout garder.
CREATE TABLE IF NOT EXISTS compute_vendor_whitelist (
  category  VARCHAR(48)  NOT NULL PRIMARY KEY,
  positions VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
