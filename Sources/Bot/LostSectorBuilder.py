from Sources.Bot.EmbedGenerator import *
from Sources.LostSector.LostSectorGenerator import *


EMOJI_MAP = {
    "Cryo": "<:Cryo:1270715011781627904>",
    "Abyssale": "<:Abyssale:1270715025660711023>",
    "Solaire": "<:Solaire:1270714993553178624>",
    "Solaires": "<:Solaire:1270714993553178624>",
    "Abyssaux": "<:Abyssale:1270715025660711023>",
    "Cryo-électriques": "<:Cryo:1270715011781627904>",
    "Brise-bouclier": "<:Bloqueur:1270042102033678388>",
    "Perturbation": "<:Surcharge:1270042140944236619>",
    "Chancellement": "<:Implacable:1270042120857849877>"
}


def format_field(data: dict, title: str) -> str:
    if not data:
        return ""
    lines = [title] + [f"> {EMOJI_MAP.get(item, item)} {count}" for item, count in data.items()]
    return "\n".join(lines)


def secteur_oublie_embed() -> discord.Embed:
    surcharges = [EMOJI_MAP.get(surcharge, surcharge) for surcharge in GetSurcharges()]
    expert_shields = GetShields(True)
    expert_champs = GetChamps(True)
    maitrise_shields = GetShields(False)
    maitrise_champs = GetChamps(False)

    expert_field_value = format_field(expert_shields, "Boucliers") + "\n" + format_field(expert_champs, "Champions")
    maitrise_field_value = format_field(maitrise_shields, "Boucliers") + "\n" + format_field(maitrise_champs, "Champions")

    fields = []

    if expert_field_value.strip():
        fields.append({"name": f"Expert ({GetPower(True)})", "value": expert_field_value.strip(), "inline": True})

    if maitrise_field_value.strip():
        fields.append({"name": f"Maitrise ({GetPower(False)})", "value": maitrise_field_value.strip(), "inline": True})

    fields.append({"name": "Surcharges", "value": " | ".join(surcharges) if surcharges else "Aucune surcharge définie", "inline": False})

    embed = create_custom_embed(
        description="## " + GetActivityName() + "\n**Récompenses**\n<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>",
        color=0xff7300,
        author="Secteur oublié du jour",
        author_icon_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png",
        thumbnail_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png",
        image_url="attachment://Output.jpeg",
        fields=fields,
        footer_text="BotOfTheDisciple",
        footer_icon_url="attachment://footer_icon.png",
        add_date_to_footer=True
    )

    return embed
