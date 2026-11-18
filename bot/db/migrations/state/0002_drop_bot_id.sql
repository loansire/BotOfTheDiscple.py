-- Une base d'état par bot : la colonne bot_id des tables bot_* ne sert plus.
-- Les lignes d'un autre bot (essais d'une base partagée) sont supprimées
-- d'abord : sans bot_id, elles deviendraient des lignes du live.
-- À appliquer en une fois : une fois une table modifiée, ses requêtes ne
-- sont plus rejouables (bot_id n'existe plus).

DELETE FROM bot_subscription WHERE bot_id <> 'live';
ALTER TABLE bot_subscription
  DROP PRIMARY KEY,
  DROP COLUMN bot_id,
  ADD PRIMARY KEY (guild_id, topic, channel_id);

DELETE FROM bot_publication WHERE bot_id <> 'live';
ALTER TABLE bot_publication
  DROP PRIMARY KEY,
  DROP COLUMN bot_id,
  ADD PRIMARY KEY (guild_id, topic);

DELETE FROM bot_message WHERE bot_id <> 'live';
ALTER TABLE bot_message
  DROP PRIMARY KEY,
  DROP COLUMN bot_id,
  ADD PRIMARY KEY (guild_id, topic, slot, position);
