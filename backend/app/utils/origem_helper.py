"""
Helper para normalização de origem/plataforma de pedidos.

Unifica o campo `marketplace_source` como identificador canônico da plataforma
de onde o pedido veio, independente de ser direto, bridge ou interno.
"""

# Plataformas externas conhecidas (delivery apps)
PLATAFORMAS_CONHECIDAS = {
    "ifood", "rappi", "99food", "keeta", "ubereats",
    "aiqfome", "zé_delivery", "goomer", "anota_ai",
}

# Mapa plataforma → label amigável para exibição
PLATAFORMA_LABELS = {
    # Internas Derekh
    "derekh_site": "Site",
    "derekh_whatsapp": "WhatsApp",
    "derekh_manual": "Manual",
    "derekh_garcom": "Garçom",
    "derekh_mesa": "Mesa",
    # Externas
    "ifood": "iFood",
    "rappi": "Rappi",
    "99food": "99Food",
    "keeta": "Keeta",
    "ubereats": "Uber Eats",
    "aiqfome": "AiQFome",
    "zé_delivery": "Zé Delivery",
    "goomer": "Goomer",
    "anota_ai": "Anota AI",
}

# Cores para badges no frontend (Tailwind classes)
PLATAFORMA_CORES = {
    "derekh_site": "blue",
    "derekh_whatsapp": "green",
    "derekh_manual": "orange",
    "derekh_garcom": "amber",
    "derekh_mesa": "amber",
    "ifood": "red",
    "rappi": "orange",
    "99food": "yellow",
    "keeta": "blue",
    "ubereats": "emerald",
    "aiqfome": "purple",
}


def normalizar_origem(origem: str | None, marketplace_source: str | None = None) -> str:
    """
    Retorna plataforma canônica a partir de origem e/ou marketplace_source.

    Prioridade:
    1. Se marketplace_source já preenchido → retorna ele
    2. Se origem começa com "bridge_" → extrai plataforma (bridge_ifood → ifood)
    3. Mapa fixo de origens internas
    4. Fallback: a própria origem ou "desconhecido"
    """
    if marketplace_source:
        return marketplace_source

    if not origem:
        return "desconhecido"

    # Bridge: bridge_ifood → ifood, bridge_rappi → rappi
    if origem.startswith("bridge_"):
        plataforma = origem[7:]  # remove "bridge_"
        if plataforma in PLATAFORMAS_CONHECIDAS:
            return plataforma
        return f"bridge_{plataforma}" if plataforma != "desconhecido" else "bridge_desconhecido"

    # Origens internas
    mapa_interno = {
        "site": "derekh_site",
        "web": "derekh_site",
        "manual": "derekh_manual",
        "garcom": "derekh_garcom",
        "mesa": "derekh_mesa",
        "whatsapp_bot": "derekh_whatsapp",
    }

    if origem in mapa_interno:
        return mapa_interno[origem]

    # Já é uma plataforma conhecida (ex: "ifood" direto)
    if origem in PLATAFORMAS_CONHECIDAS:
        return origem

    return origem


def get_plataforma_label(plataforma: str) -> str:
    """Retorna label amigável para exibição. Fallback: capitalizar."""
    if plataforma in PLATAFORMA_LABELS:
        return PLATAFORMA_LABELS[plataforma]
    # Fallback: "bridge_bobsfood" → "Bobsfood (Bridge)"
    if plataforma.startswith("bridge_"):
        nome = plataforma[7:].replace("_", " ").title()
        return f"{nome} (Bridge)"
    return plataforma.replace("_", " ").title()


def get_plataforma_cor(plataforma: str) -> str:
    """Retorna nome da cor para a plataforma. Fallback: cyan."""
    return PLATAFORMA_CORES.get(plataforma, "cyan")
