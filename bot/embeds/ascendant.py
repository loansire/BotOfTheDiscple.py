# -*- coding: utf-8 -*-
"""Rendu Components V2 des Défis ascendants.

Un unique message persistant, ÉDITÉ en place à chaque reset hebdo (aucun ping) :
- en-tête + défi ACTIF (secteur, type d'entrée, malédiction, position de Petra)
  + image pleine largeur optionnelle + fin de semaine ;
- séparateur ;
- liste des défis SUIVANTS (cycle complet SANS doublon), chacun avec sa semaine
  de début et sa phase de malédiction.

Les heures sont rendues en timestamps dynamiques Discord (fuseau de chaque
utilisateur). L'image vit dans Ressources/Ascendant/<clé>.png ; si absente, on
affiche le texte sans image (placeholder tolérant).

hash_contrat optionnel : contrat Petra (composant 402) passé en override de
validation. Par défaut None → résolution par la formule déterministe."""
from __future__ import annotations

import discord
from discord import ui

from bot.config import RESOURCES_DIR
from bot.features.ascendant import AscendantWindow, resolve
from bot.features.ascendant.constants import ASCENDANT_EMOJI, image_filename

_ACCENT = discord.Color(0x7A5FB8)  # violet « ascendant » (plan Ascendant)
ASCENDANT_DIR = RESOURCES_DIR / "Ascendant"

_MALEDICTION_LABEL = {
    "faible": "Faible",
    "croissante": "Croissante",
    "forte": "Forte",
}


class AscendantView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, container: ui.Container):
        super().__init__(timeout=None)
        self.add_item(container)


def _image_file(challenge: str) -> discord.File | None:
    """Image du défi si présente, sinon placeholder.png, sinon rien (texte seul)."""
    for fname in (image_filename(challenge), "placeholder.png"):
        path = ASCENDANT_DIR / fname
        if path.is_file():
            return discord.File(path, filename=fname)
    return None


def _mal(label: str) -> str:
    return _MALEDICTION_LABEL.get(label, label)


def _active_block(meta: dict, win: AscendantWindow) -> str:
    return (
        f"# {ASCENDANT_EMOJI} Défi ascendant de la semaine\n"
        f"## {meta['nom']}\n"
        f"**Lieu :** {meta['secteur']} - *{meta['entree']}*\n"
        f"**Malédiction :** {_mal(meta['malediction'])}"
        f"  •  **Petra :** {meta['petra']}\n"
        f"-# Actualisation : <t:{win.end_unix}:F> (<t:{win.end_unix}:R>)"
    )


def content_hash(now=None, hash_contrat: int | None = None) -> str:
    """Identité du contenu = semaine + défi résolu. Change chaque semaine (ou si
    un contrat live diverge) → déclenche l'édition du message."""
    state = resolve(hash_contrat, now)
    return f"ascendant:{state['window'].index}:{state['cle']}"


def build_ascendant_view(
    now=None, hash_contrat: int | None = None
) -> tuple[AscendantView, list[discord.File]]:
    """Construit (vue, fichiers NEUFS) pour l'état à `now`.

    Un discord.File est consommé après envoi : renvoyer des File neufs à chaque
    appel est indispensable. hash_contrat optionnel (override de validation)."""
    state = resolve(hash_contrat, now)
    win: AscendantWindow = state["window"]
    meta = {k: state[k] for k in ("nom", "secteur", "entree", "malediction", "petra")}

    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(_active_block(meta, win)))

    img = _image_file(state["cle"])
    if img is not None:
        files.append(img)
        container.add_item(
            ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{img.filename}"))
        )

    return AscendantView(container), files