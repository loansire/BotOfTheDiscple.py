-- Contenu partagé (content_*) : publications prêtes à afficher, écrites par
-- le calcul (bot live) et lues telles quelles par chaque bot qui publie.
-- 1 composant Discord = 1 ligne de content_component, texte déjà formaté.

-- Une ligne par version d'une publication. La version courante d'un topic
-- est la plus grande version au statut 'ready'.
CREATE TABLE IF NOT EXISTS content_post (
  topic        VARCHAR(48)  NOT NULL,
  version      INT UNSIGNED NOT NULL,
  mode         VARCHAR(16)  NOT NULL COMMENT 'repost / edit / event / on_demand',
  content_hash CHAR(40)     NOT NULL COMMENT 'sha1 de tout le contenu rendu',
  period_start DATETIME     NULL COMMENT 'UTC',
  expires_at   DATETIME     NULL COMMENT 'UTC, indicatif',
  status       VARCHAR(16)  NOT NULL DEFAULT 'ready',
  computed_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (topic, version),
  KEY idx_computed_at (computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Les messages d'une version, dans l'ordre d'envoi. variant : 'default',
-- ou 'en' / 'fr' (news), 'p1'..'pN' (pages), etc.
CREATE TABLE IF NOT EXISTS content_message (
  topic        VARCHAR(48)       NOT NULL,
  version      INT UNSIGNED      NOT NULL,
  variant      VARCHAR(32)       NOT NULL DEFAULT 'default',
  position     SMALLINT UNSIGNED NOT NULL,
  layout       VARCHAR(16)       NOT NULL COMMENT 'components_v2 / embed',
  accent_color INT UNSIGNED      NULL,
  PRIMARY KEY (topic, version, variant, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Un composant = une ligne, dans l'ordre d'affichage.
CREATE TABLE IF NOT EXISTS content_component (
  topic        VARCHAR(48)       NOT NULL,
  version      INT UNSIGNED      NOT NULL,
  variant      VARCHAR(32)       NOT NULL DEFAULT 'default',
  message_pos  SMALLINT UNSIGNED NOT NULL,
  position     SMALLINT UNSIGNED NOT NULL,
  kind         VARCHAR(24)       NOT NULL,
  text         TEXT              NULL COMMENT 'markdown final',
  title        VARCHAR(256)      NULL COMMENT 'nom de champ / auteur, placeholder',
  url          VARCHAR(512)      NULL COMMENT 'lien cliquable',
  image_url    VARCHAR(512)      NULL COMMENT 'image distante',
  image_id     CHAR(40)          NULL COMMENT 'image stockée (content_image)',
  image_name   VARCHAR(128)      NULL COMMENT 'nom de la pièce jointe',
  inline_field TINYINT(1)        NULL,
  btn_label    VARCHAR(100)      NULL,
  btn_emoji    VARCHAR(100)      NULL,
  btn_style    VARCHAR(16)       NULL COMMENT 'primary / secondary / success / danger',
  btn_action   VARCHAR(100)      NULL COMMENT 'custom_id ou valeur d option',
  btn_disabled TINYINT(1)        NULL,
  PRIMARY KEY (topic, version, variant, message_pos, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Images (générées ou statiques), stockées une seule fois par contenu.
CREATE TABLE IF NOT EXISTS content_image (
  image_id   CHAR(40)    NOT NULL PRIMARY KEY COMMENT 'sha1 des octets',
  mime       VARCHAR(32) NOT NULL,
  data       MEDIUMBLOB  NOT NULL,
  created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
