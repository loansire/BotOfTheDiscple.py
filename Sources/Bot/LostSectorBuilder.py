from Sources.Bot.EmbedGenerator import *
from Sources.LostSector.LostSectorGenerator import *


EMOJI_MAP = {
    "Cryo": "<:Cryo:1270715011781627904>",
    "Cryo-électriques": "<:Cryo:1270715011781627904>",
    "Abyssale": "<:Abyssale:1270715025660711023>",
    "Abyssales": "<:Abyssale:1270715025660711023>",
    "Abyssaux": "<:Abyssale:1270715025660711023>",
    "Solaire": "<:Solaire:1270714993553178624>",
    "Solaires": "<:Solaire:1270714993553178624>",
    "Stase": "<:Stase:1293381064869285938>",
    "Stases": "<:Stase:1293381064869285938>",
    "Filobscur": "<:Filobscure:1293381094774931456>",
    "Filobscurs": "<:Filobscure:1293381094774931456>",
    "Brise-bouclier": "<:Bloqueur:1270042102033678388>",
    "Brise-boucliers": "<:Bloqueur:1270042102033678388>",
    "Perturbation": "<:Surcharge:1270042140944236619>",
    "Perturbations": "<:Surcharge:1270042140944236619>",
    "Chancellement": "<:Implacable:1270042120857849877>",
    "Chancellements": "<:Implacable:1270042120857849877>",

    "Torse":"<:Torse:1352430868756697099>",
    "Casque":"<:Casque:1352430820802957403>",
    "Jambes":"<:Jambes:1352430853036310600>",
    "Bras":"<:Bras:1352430835881480322>",

    "Arc": "<:Arc:1305317528079437955>",
    "Epée": "<:Epee:1305317544684556370>",
    "Fusil à Impulsion": "<:Fusilaimpulsion:1305317558748057661>",
    "Fusil à Pompe": "<:Fusilapompe:1305317574585745408>",
    "Fusil à Rayon": "<:Fusilarayon:1305317604839264257>",
    "Fusil Automatique": "<:Fusilautomatique:1305317622266462238>",
    "Fusil d'Eclaireur": "<:Fusildeclaireur:1305317638158942248>",
    "Fusil de Précision": "<:Fusildeprecision:1305317655221375026>",
    "Fusion": "<:Fusion:1305317671889403925>",
    "Fusion Lineaire": "<:Fusionlineaire:1305317687894999060>",
    "Glaive": "<:Glaive:1305317709751259147>",
    "Lance Grenades Léger": "<:Lancegrenadesleger:1305317726125948968>",
    "Lance Grenades Lourd": "<:Lancegrenadeslourd:1305317747349000192>",
    "Lance Roquettes": "<:Lanceroquettes:1305317762712735744>",
    "Mitrailleuse": "<:Mitrailleuse:1305317781029388378>",
    "Pistolet": "<:Pistolet:1305317796908892160>",
    "Pistolet Mitrailleur": "<:Pistoletmitrailleur:1305317813094711416>",
    "Revolver": "<:Revolver:1305317829653823608>",

    "Principale":"<:Principale:1352409012511051799>",
    "Spéciale":"<:Speciale:1352409042538070016>",
    "Lourde":"<:Lourde:1352409107273093191>",
}

WEAPON_TYPE_MAP = {
    "None": 0,
    "Fusil Automatique": 6,
    "Fusil à Pompe": 7,
    "Mitrailleuse": 8,
    "Revolver": 9,
    "Lance Roquettes": 10,
    "FusionRifle": 11,
    "Fusil de Précision": 12,
    "Fusil à Impulsion": 13,
    "Fusil d'Eclaireur": 14,
    "Pistolet": 17,
    "Epée": 18,
    "Fusion Lineaire": 22,
    "Lance Grenades": 23,
    "Pistolet Mitrailleur": 24,
    "Fusil à Rayon": 25,
    "Arc": 31,
    "Glaive": 33,
}
WEAPON_DAMAGES_TYPE_MAP = {
    "None": 0,
    "Cinétiques": 1,
    "Cryo-électriques": 2,
    "Thermal": 3,
    "Abyssaux": 4,
    "Raid": 5,
    "Stase": 6,
    "Filobscur": 7,
}
WEAPON_MUNITIONS_TYPE_MAP = {
    "None": 0,
    "Principale": 1,
    "Spéciale": 2,
    "Lourde": 3,
    "Inconnue": 4,
}


def format_field(data: dict, title: str) -> str:
    if not data:
        return ""
    lines = [title] + [f"> {EMOJI_MAP.get(item, item)} {count}" for item, count in data.items()]
    return "\n".join(lines)

def lostsector_infos():
    infos = JsonDatabase.GetInformations(Config.LOSTSECTOR)
    return infos

def secteur_oublie_embed():
    infos = lostsector_infos()

    expert_shields = infos[JsonDbDefines.SHIELDS_EXPERT]
    expert_champs = infos[JsonDbDefines.CHAMPS_EXPERT]
    maitrise_shields = infos[JsonDbDefines.SHIELDS_MASTER]
    maitrise_champs = infos[JsonDbDefines.CHAMPS_MASTER]
    activity_name = infos[JsonDbDefines.ACTIVITY_NAME]
    power_expert = infos[JsonDbDefines.POWER_EXPERT]
    power_master = infos[JsonDbDefines.POWER_MASTER]

    surcharges = [EMOJI_MAP.get(surcharge, surcharge) for surcharge in
                  [infos[JsonDbDefines.SURCHARGE1], infos[JsonDbDefines.SURCHARGE2]]]
    expert_field_value = format_field(expert_shields, "Boucliers") + "\n" + format_field(expert_champs, "Champions")
    maitrise_field_value = format_field(maitrise_shields, "Boucliers") + "\n" + format_field(maitrise_champs, "Champions")

    fields = []

    if expert_field_value.strip():
        fields.append({
            "name": f"Expert ({power_expert})",
            "value": expert_field_value.strip(),
            "inline": True
        })

    if maitrise_field_value.strip():
        fields.append({
            "name": f"Maitrise ({power_master})",
            "value": maitrise_field_value.strip(),
            "inline": True
        })

    image_path = "Output/Output.png"  # Assurez-vous que le chemin et l'extension correspondent

    image_file = discord.File(image_path, filename="Output.png")  # Assurez-vous que le nom du fichier correspond

    files = [image_file] if image_file else []  # Assurer que files est une liste même si elle est vide

    # Création de l'embed avec la fonction générique
    embed, components, _ = create_embed_with_components(
        description="## " + activity_name + "\n**Surcharges**\n" + " | ".join(surcharges) if surcharges else "Aucune surcharge définie",
        color=0xff7300,
        author="Secteur oublié du jour",
        author_icon_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png",
        thumbnail_url="https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_7d11acd7d5a3daebc0a0c906452932d6.png",
        image_url="attachment://Output.png",
        fields=fields,
        footer_text=None,
        footer_icon_url=None,
        add_date_to_footer=True,
        buttons=None,
        files=None
    )

    return embed, files

def secteur_oublie_Loot_embed():
    infos = JsonDatabase.GetInformations(Config.LOSTSECTOR)
    loot_details = infos["Loot"]["Weapons Detail"]
    focus_armor = infos["Loot"]["Focus Armor"]

    fields = []

    # Ajout des armes (toutes)
    for idx, weapon in enumerate(loot_details):
        weapon_name = weapon["Name"]
        weapon_hash = weapon["Hash"]
        weapon_type = next((k for k, v in WEAPON_TYPE_MAP.items() if v == weapon["Weapon Type"]), "Inconnu")
        ammo_type = next((k for k, v in WEAPON_MUNITIONS_TYPE_MAP.items() if v == weapon["Munitions Type"]), "Inconnue")
        damage_type = next((k for k, v in WEAPON_DAMAGES_TYPE_MAP.items() if v == weapon["Damage Type"]), "Inconnu")

        # Condition spéciale pour Lance Grenades (Léger ou Lourd)
        if weapon_type == "Lance Grenades":
            if ammo_type == "Lourde":
                weapon_type = "Lance Grenades Lourd"
            else:
                weapon_type = "Lance Grenades Léger"

        # Ajout des emotes
        weapon_type_emoji = EMOJI_MAP.get(weapon_type, "")
        ammo_type_emoji = EMOJI_MAP.get(ammo_type, "")
        damage_type_emoji = EMOJI_MAP.get(damage_type, "")

        fields.append({
            "name": "",
            "value": f"**{weapon_name}**\n"
                     f"[ᶠʳ ᴸᶦᵍʰᵗᴳᴳ](<https://www.light.gg/db/fr/items/{weapon_hash}>) • [ᵉⁿ ᶠᵒᵘⁿᵈʳʸ](<https://d2foundry.gg/w/{weapon_hash}>)\n"
                     f"{weapon_type_emoji} | {ammo_type_emoji} | {damage_type_emoji}",
            "inline": True
        })

    footer_icon_path = "Ressources/footer_icon.png"
    footer_icon_file = discord.File(footer_icon_path, filename="footer_icon.png")

    focus_armor_image_path = f"Ressources/Rahol/{focus_armor}.png"
    focus_armor_image_file = discord.File(focus_armor_image_path, filename=f"focus_armor.png")

    files = [footer_icon_file, focus_armor_image_file] if focus_armor_image_file else [footer_icon_file]  # Assurer que files est une liste même si elle est vide

    # Création de l'embed
    embed, components, _ = create_embed_with_components(
        description="## Décryptage Focus du jour\n**Récompenses de secteur oublié**\n<:Engramme_Exo:1270719580322660425> | <:Lengendaire:1270719601646374954> | <:Matrice:1270042340324544604>",
        color=0xff7300,
        author=None,
        author_icon_url=None,
        thumbnail_url="attachment://focus_armor.png",
        image_url=None,
        fields=fields,
        footer_text="Infographie générée par Sisimonis et Loan#5197",
        footer_icon_url="attachment://footer_icon.png",
        add_date_to_footer=True,
        buttons=None,
        files=files
    )

    return embed, files



