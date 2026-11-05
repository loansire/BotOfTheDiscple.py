# -*- coding: utf-8 -*-
"""Modèle d'affichage partagé entre le calcul et la publication.

Le calcul (bot live) construit des `Post` ENTIÈREMENT résolus : textes déjà
formatés (markdown, emojis, liens, timestamps `<t:…>`), images déjà générées,
découpage en messages déjà fait. Le côté publication ne fait que lire ces
objets en base et les convertir mécaniquement en composants Discord (cf.
bot/render/components.py) : 1 Component = 1 composant Discord.

Kinds d'un message Components V2 (dans le Container) :
    text       TextDisplay(text)
    section    Section(TextDisplay(text), accessory=Thumbnail(image))
    gallery    MediaGallery(image)
    separator  Separator()
    button     Button (les boutons consécutifs partagent une ActionRow)
    select     Select (title = placeholder, btn_action = custom_id), suivi de
    option     ses options (btn_label, btn_action = valeur, btn_emoji)

Kinds d'un message embed :
    embed_author       nom = title, lien = url, icône = image
    embed_description  text
    embed_field        nom = title, valeur = text, inline
    embed_thumbnail    image
    embed_image        image
    embed_footer       text, icône = image
    button / select / option   comme ci-dessus, sous l'embed

Une image est soit stockée en base (`image_id` + `image_name`, jointe au
message), soit distante (`image_url`). À la construction, le calcul fournit
les octets dans `image_data` ; l'écriture en base les remplace par leur id."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

CV2 = "components_v2"
EMBED = "embed"

DEFAULT_VARIANT = "default"


@dataclass
class Component:
    kind: str
    text: str | None = None
    title: str | None = None
    url: str | None = None
    image_url: str | None = None
    image_id: str | None = None
    image_name: str | None = None
    inline_field: bool | None = None
    btn_label: str | None = None
    btn_emoji: str | None = None
    btn_style: str | None = None
    btn_action: str | None = None
    btn_disabled: bool | None = None
    # Octets de l'image à stocker (construction seulement, jamais relus).
    image_data: bytes | None = field(default=None, repr=False, compare=False)
    image_mime: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.image_data is not None and self.image_id is None:
            self.image_id = image_id_of(self.image_data)

    def row(self) -> dict:
        """Colonnes persistées (sans les octets)."""
        data = asdict(self)
        data.pop("image_data")
        data.pop("image_mime")
        return data


@dataclass
class Message:
    layout: str = CV2
    accent_color: int | None = None
    components: list[Component] = field(default_factory=list)

    def add(self, component: Component) -> "Message":
        self.components.append(component)
        return self


@dataclass
class Post:
    topic: str
    mode: str  # repost / edit / event / on_demand
    variants: dict[str, list[Message]] = field(default_factory=dict)
    period_start: datetime | None = None
    expires_at: datetime | None = None
    version: int | None = None  # renseigné à la lecture / après écriture

    @property
    def messages(self) -> list[Message]:
        return self.variants.get(DEFAULT_VARIANT, [])

    def images(self) -> dict[str, tuple[bytes, str]]:
        """id → (octets, mime) des images à stocker."""
        return {
            c.image_id: (c.image_data, c.image_mime or "image/webp")
            for messages in self.variants.values()
            for m in messages
            for c in m.components
            if c.image_data is not None
        }

    def content_hash(self) -> str:
        """sha1 de TOUT le contenu rendu (textes, boutons, ids d'images...)."""
        canonical = {
            variant: [
                {"layout": m.layout, "accent": m.accent_color, "components": [c.row() for c in m.components]}
                for m in messages
            ]
            for variant, messages in sorted(self.variants.items())
        }
        raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def image_id_of(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


# ── Constructeurs (côté calcul) ─────────────────────────────────────────


def text(content: str) -> Component:
    return Component("text", text=content)


def separator() -> Component:
    return Component("separator")


def image(kind: str, data: bytes, name: str, *, mime: str = "image/webp", **extra) -> Component:
    """Composant portant une image stockée (section, gallery, embed_*)."""
    return Component(kind, image_data=data, image_mime=mime, image_name=name, **extra)


def button(label: str | None, action: str, *, emoji: str | None = None,
           style: str = "secondary", disabled: bool = False) -> Component:
    return Component(
        "button", btn_label=label, btn_action=action, btn_emoji=emoji,
        btn_style=style, btn_disabled=disabled,
    )
