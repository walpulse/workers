"""i18n strings for analisis_pdf (es | en | pt)."""

from __future__ import annotations

from typing import Any

Lang = str  # "es" | "en" | "pt"

SUPPORTED_LANGS = frozenset({"es", "en", "pt"})

TIER_LABELS: dict[str, dict[str, str]] = {
    "estandar": {"es": "Estándar", "en": "Standard", "pt": "Padrão"},
    "experta": {"es": "Experta", "en": "Expert", "pt": "Expert"},
    "basica": {"es": "Básica", "en": "Basic", "pt": "Básica"},
}

MODULE_NAMES: dict[str, dict[str, str]] = {
    "origins": {"es": "Orígenes", "en": "Origins", "pt": "Origens"},
    "activity": {"es": "Actividad", "en": "Activity", "pt": "Atividade"},
    "multichain": {"es": "Multichain", "en": "Multichain", "pt": "Multichain"},
    "portfolio": {"es": "Portafolio", "en": "Portfolio", "pt": "Portfólio"},
}

MODULE_ORDER = ("origins", "activity", "multichain", "portfolio")

# key -> {es, en, pt} — every flat signal key shown in the PDF must live here.
SIGNAL_LABELS: dict[str, dict[str, str]] = {
    "hhi": {"es": "HHI", "en": "HHI", "pt": "HHI"},
    "hhi_usd": {"es": "HHI USD", "en": "HHI USD", "pt": "HHI USD"},
    "unique_senders": {
        "es": "Remitentes únicos",
        "en": "Unique senders",
        "pt": "Remetentes únicos",
    },
    "unique_senders_sum": {
        "es": "Remitentes únicos (suma)",
        "en": "Unique senders (sum)",
        "pt": "Remetentes únicos (soma)",
    },
    "unique_counterparties": {
        "es": "Contrapartes únicas",
        "en": "Unique counterparties",
        "pt": "Contrapartes únicas",
    },
    "unique_counterparties_sum": {
        "es": "Contrapartes únicas (suma)",
        "en": "Unique counterparties (sum)",
        "pt": "Contrapartes únicas (soma)",
    },
    "counterparty_hhi": {
        "es": "HHI de contrapartes",
        "en": "Counterparty HHI",
        "pt": "HHI de contrapartes",
    },
    "priced_coverage_pct": {
        "es": "Cobertura de pricing",
        "en": "Priced coverage",
        "pt": "Cobertura de pricing",
    },
    "sanctions_hit": {
        "es": "Exposición a sanciones",
        "en": "Sanctions exposure",
        "pt": "Exposição a sanções",
    },
    "sanctions_hit_any": {
        "es": "Exposición a sanciones (cualquier)",
        "en": "Sanctions exposure (any)",
        "pt": "Exposição a sanções (qualquer)",
    },
    "mixing_risk": {
        "es": "Riesgo de mixing",
        "en": "Mixing risk",
        "pt": "Risco de mixing",
    },
    "sourcify_verified_pct": {
        "es": "Sourcify verificado",
        "en": "Sourcify verified",
        "pt": "Sourcify verificado",
    },
    "kleros_tagged_counterparty_pct": {
        "es": "Contrapartes etiquetadas Kleros",
        "en": "Kleros-tagged counterparties",
        "pt": "Contrapartes etiquetadas Kleros",
    },
    "spellbook_labeled_pct": {
        "es": "Etiquetado Spellbook",
        "en": "Spellbook labeled",
        "pt": "Etiquetado Spellbook",
    },
    "unverified_contract_pct": {
        "es": "Contratos no verificados",
        "en": "Unverified contracts",
        "pt": "Contratos não verificados",
    },
    "unverified_token_exposure_pct": {
        "es": "Exposición a tokens no verificados",
        "en": "Unverified token exposure",
        "pt": "Exposição a tokens não verificados",
    },
    "active_chains_30d": {
        "es": "Chains activas (30d)",
        "en": "Active chains (30d)",
        "pt": "Chains ativas (30d)",
    },
    "active_chains_90d": {
        "es": "Chains activas (90d)",
        "en": "Active chains (90d)",
        "pt": "Chains ativas (90d)",
    },
    "total_chains_with_activity": {
        "es": "Chains con actividad",
        "en": "Chains with activity",
        "pt": "Chains com atividade",
    },
    "activity_span_days": {
        "es": "Span de actividad (días)",
        "en": "Activity span (days)",
        "pt": "Span de atividade (dias)",
    },
    "dormant_ratio": {
        "es": "Ratio de dormidas",
        "en": "Dormant ratio",
        "pt": "Razão de dormidas",
    },
    "footprint_span_hhi": {
        "es": "HHI de footprint",
        "en": "Footprint HHI",
        "pt": "HHI de footprint",
    },
    "recency_days": {
        "es": "Recencia (días)",
        "en": "Recency (days)",
        "pt": "Recência (dias)",
    },
    "consistency": {
        "es": "Consistencia",
        "en": "Consistency",
        "pt": "Consistência",
    },
    "wash_score": {
        "es": "Puntaje wash",
        "en": "Wash score",
        "pt": "Pontuação wash",
    },
    "bot_like_score": {
        "es": "Puntaje bot-like",
        "en": "Bot-like score",
        "pt": "Pontuação bot-like",
    },
    "ofac_exposure_pct_value": {
        "es": "Exposición OFAC (% valor)",
        "en": "OFAC exposure (% value)",
        "pt": "Exposição OFAC (% valor)",
    },
    "mixer_exposure_pct_value": {
        "es": "Exposición mixer (% valor)",
        "en": "Mixer exposure (% value)",
        "pt": "Exposição mixer (% valor)",
    },
    "bridge_exposure_pct_value": {
        "es": "Exposición bridge (% valor)",
        "en": "Bridge exposure (% value)",
        "pt": "Exposição bridge (% valor)",
    },
    "airdrop_exposure_pct_value": {
        "es": "Exposición airdrop (% valor)",
        "en": "Airdrop exposure (% value)",
        "pt": "Exposição airdrop (% valor)",
    },
    "protocol_exposure_pct_value": {
        "es": "Exposición protocolo (% valor)",
        "en": "Protocol exposure (% value)",
        "pt": "Exposição protocolo (% valor)",
    },
    "protocol_exposure_count": {
        "es": "Exposiciones a protocolos (conteo)",
        "en": "Protocol exposures (count)",
        "pt": "Exposições a protocolos (contagem)",
    },
    "organic_vs_synthetic": {
        "es": "Orgánico vs sintético",
        "en": "Organic vs synthetic",
        "pt": "Orgânico vs sintético",
    },
    "direct_exposure": {
        "es": "Exposición directa",
        "en": "Direct exposure",
        "pt": "Exposição direta",
    },
    "concentration": {
        "es": "Concentración",
        "en": "Concentration",
        "pt": "Concentração",
    },
    "window_days": {
        "es": "Ventana (días)",
        "en": "Window (days)",
        "pt": "Janela (dias)",
    },
    "contract_interactions_total": {
        "es": "Interacciones con contratos",
        "en": "Contract interactions",
        "pt": "Interações com contratos",
    },
    "chains_ok": {
        "es": "Chains OK",
        "en": "Chains OK",
        "pt": "Chains OK",
    },
    "credible_value_usd": {
        "es": "Valor credible (USD)",
        "en": "Credible value (USD)",
        "pt": "Valor credible (USD)",
    },
    "usable_value_usd": {
        "es": "Valor usable (USD)",
        "en": "Usable value (USD)",
        "pt": "Valor utilizável (USD)",
    },
    "total_value_usd": {
        "es": "Valor total (USD)",
        "en": "Total value (USD)",
        "pt": "Valor total (USD)",
    },
    "total_value_usd_credible": {
        "es": "Valor total credible (USD)",
        "en": "Total credible value (USD)",
        "pt": "Valor total credible (USD)",
    },
    "liquid_ratio": {
        "es": "Ratio líquido",
        "en": "Liquid ratio",
        "pt": "Razão líquida",
    },
    "liquid_usd": {
        "es": "Valor líquido (USD)",
        "en": "Liquid value (USD)",
        "pt": "Valor líquido (USD)",
    },
    "locked_usd": {
        "es": "Valor bloqueado (USD)",
        "en": "Locked value (USD)",
        "pt": "Valor bloqueado (USD)",
    },
    "locked_commitment_score": {
        "es": "Puntaje de compromiso bloqueado",
        "en": "Locked commitment score",
        "pt": "Pontuação de compromisso bloqueado",
    },
    "holdings_hhi": {
        "es": "HHI de holdings",
        "en": "Holdings HHI",
        "pt": "HHI de holdings",
    },
    "dust_pct": {
        "es": "Dust",
        "en": "Dust",
        "pt": "Dust",
    },
    "dust_count": {
        "es": "Posiciones dust (conteo)",
        "en": "Dust positions (count)",
        "pt": "Posições dust (contagem)",
    },
    "dust_ratio": {
        "es": "Ratio dust",
        "en": "Dust ratio",
        "pt": "Razão dust",
    },
    "spam_count": {
        "es": "Posiciones spam (conteo)",
        "en": "Spam positions (count)",
        "pt": "Posições spam (contagem)",
    },
    "effective_positions": {
        "es": "Posiciones efectivas",
        "en": "Effective positions",
        "pt": "Posições efetivas",
    },
    "positions_sampled": {
        "es": "Posiciones muestreadas",
        "en": "Positions sampled",
        "pt": "Posições amostradas",
    },
    "native_gas_buffer_usd": {
        "es": "Buffer de gas nativo (USD)",
        "en": "Native gas buffer (USD)",
        "pt": "Buffer de gas nativo (USD)",
    },
    "native_gas_buffer_positions": {
        "es": "Posiciones buffer de gas",
        "en": "Gas buffer positions",
        "pt": "Posições buffer de gas",
    },
    "core_ecosystems": {
        "es": "Ecosistemas core",
        "en": "Core ecosystems",
        "pt": "Ecossistemas core",
    },
    "main_chains": {
        "es": "Chains principales",
        "en": "Main chains",
        "pt": "Chains principais",
    },
    "defi_lp_split": {
        "es": "Split DeFi / LP",
        "en": "DeFi / LP split",
        "pt": "Split DeFi / LP",
    },
    "longevity_flags": {
        "es": "Flags de longevidad",
        "en": "Longevity flags",
        "pt": "Flags de longevidade",
    },
    "shares": {
        "es": "Participaciones",
        "en": "Shares",
        "pt": "Participações",
    },
    "version": {
        "es": "Versión",
        "en": "Version",
        "pt": "Versão",
    },
    "grade": {
        "es": "Grade (señal)",
        "en": "Grade (signal)",
        "pt": "Grade (sinal)",
    },
}

UI: dict[str, dict[str, str]] = {
    "page_title": {
        "es": "Walpulse — Análisis de wallet",
        "en": "Walpulse — Wallet analysis",
        "pt": "Walpulse — Análise de wallet",
    },
    "doc_title": {
        "es": "Análisis de wallet",
        "en": "Wallet analysis",
        "pt": "Análise de wallet",
    },
    "wallet_label": {
        "es": "WALLET ANALIZADA:",
        "en": "ANALYZED WALLET:",
        "pt": "WALLET ANALISADA:",
    },
    "date_label": {
        "es": "FECHA ANALISIS:",
        "en": "ANALYSIS DATE:",
        "pt": "DATA DA ANÁLISE:",
    },
    "compliance_title": {
        "es": "Compliance screen OFAC",
        "en": "OFAC compliance screen",
        "pt": "Compliance screen OFAC",
    },
    "verdict": {"es": "Veredicto", "en": "Verdict", "pt": "Veredito"},
    "sanctioned": {"es": "Sancionado", "en": "Sanctioned", "pt": "Sancionado"},
    "signature_verified": {
        "es": "Firma verificada",
        "en": "Signature verified",
        "pt": "Assinatura verificada",
    },
    "unavailable": {
        "es": "No disponible",
        "en": "Unavailable",
        "pt": "Indisponível",
    },
    "yes": {"es": "Sí", "en": "Yes", "pt": "Sim"},
    "no": {"es": "No", "en": "No", "pt": "Não"},
    "na": {"es": "n/d", "en": "n/a", "pt": "n/d"},
    "origins_hops_title": {
        "es": "Hops / fondeadores analizados",
        "en": "Hops / analyzed funders",
        "pt": "Hops / financiadores analisados",
    },
    "activity_lights_title": {
        "es": "Contrapartes top analizadas",
        "en": "Top analyzed counterparties",
        "pt": "Contrapartes top analisadas",
    },
    "hop_level_direct": {
        "es": "Hop {n} — fondeadores directos",
        "en": "Hop {n} — direct funders",
        "pt": "Hop {n} — financiadores diretos",
    },
    "hop_level_via": {
        "es": "Hop {n} — segundo nivel",
        "en": "Hop {n} — second level",
        "pt": "Hop {n} — segundo nível",
    },
    "hop_orphans_title": {
        "es": "Hop 2 — sin hop 1 vinculado",
        "en": "Hop 2 — no linked hop 1",
        "pt": "Hop 2 — sem hop 1 vinculado",
    },
    "via_label": {
        "es": "Wallet fondeada",
        "en": "Funded wallet",
        "pt": "Carteira financiada",
    },
    "chains_section_title": {
        "es": "Chains con actividad",
        "en": "Chains with activity",
        "pt": "Chains com atividade",
    },
    "chain_col_name": {
        "es": "Chain",
        "en": "Chain",
        "pt": "Chain",
    },
    "chain_col_last_tx": {
        "es": "Última tx",
        "en": "Last tx",
        "pt": "Última tx",
    },
    "overview_title": {
        "es": "Vista general",
        "en": "Overview",
        "pt": "Visão geral",
    },
    "hop_label": {"es": "Hop", "en": "Hop", "pt": "Hop"},
    "grade_label": {"es": "Grade", "en": "Grade", "pt": "Grade"},
    "weight_label": {"es": "Peso", "en": "Weight", "pt": "Peso"},
    "weight_share_label": {
        "es": "Peso relativo",
        "en": "Relative weight",
        "pt": "Peso relativo",
    },
    "module_fallback": {
        "es": "Módulo calificado {grade}.",
        "en": "Module graded {grade}.",
        "pt": "Módulo classificado {grade}.",
    },
    "synthesis_fallback": {
        "es": "Calificación {grade}",
        "en": "Grade {grade}",
        "pt": "Classificação {grade}",
    },
    "disclaimer_fallback": {
        "es": (
            "Este análisis es una señal point-in-time. "
            "No garantiza comportamiento futuro ni sustituye debida diligencia del receptor."
        ),
        "en": (
            "This analysis is a point-in-time signal. "
            "It does not guarantee future behavior or replace the recipient's due diligence."
        ),
        "pt": (
            "Esta análise é um sinal point-in-time. "
            "Não garante comportamento futuro nem substitui a devida diligência do receptor."
        ),
    },
    "ipfs_both": {
        "es": (
            "Si desea mayor información sobre este análisis puede consultar el siguiente archivo IPFS: "
            "{analisis_link} o si desea constatar la información usada para ejecutar este análisis "
            "puede consultar el siguiente archivo IPFS {evidencia_link}."
        ),
        "en": (
            "For more information about this analysis, see the following IPFS file: "
            "{analisis_link} or to verify the information used to run this analysis, "
            "see the following IPFS file {evidencia_link}."
        ),
        "pt": (
            "Para mais informações sobre esta análise, consulte o seguinte arquivo IPFS: "
            "{analisis_link} ou para constatar as informações usadas para executar esta análise, "
            "consulte o seguinte arquivo IPFS {evidencia_link}."
        ),
    },
    "ipfs_analisis": {
        "es": (
            "Si desea mayor información sobre este análisis puede consultar el siguiente archivo IPFS: "
            "{analisis_link}."
        ),
        "en": (
            "For more information about this analysis, see the following IPFS file: "
            "{analisis_link}."
        ),
        "pt": (
            "Para mais informações sobre esta análise, consulte o seguinte arquivo IPFS: "
            "{analisis_link}."
        ),
    },
    "ipfs_evidencia": {
        "es": (
            "Si desea constatar la información usada para ejecutar este análisis puede consultar "
            "el siguiente archivo IPFS {evidencia_link}."
        ),
        "en": (
            "To verify the information used to run this analysis, see the following IPFS file "
            "{evidencia_link}."
        ),
        "pt": (
            "Para constatar as informações usadas para executar esta análise, consulte "
            "o seguinte arquivo IPFS {evidencia_link}."
        ),
    },
    "id_label": {
        "es": "Identificación:",
        "en": "Identification:",
        "pt": "Identificação:",
    },
    "footer_wallet_label": {
        "es": "Wallet:",
        "en": "Wallet:",
        "pt": "Wallet:",
    },
    "footer_date_label": {
        "es": "Fecha:",
        "en": "Date:",
        "pt": "Data:",
    },
    "footer_created_by": {
        "es": "Análisis creado y distribuido por Walpulse",
        "en": "Analysis created and distributed by Walpulse",
        "pt": "Análise criada e distribuída por Walpulse",
    },
    "footer_signals_disclaimer": {
        "es": "Este análisis produce señales, no debe ser decisorio por sí solo",
        "en": "This analysis produces signals; it must not be decisive on its own",
        "pt": "Esta análise produz sinais; não deve ser decisória por si só",
    },
    "data_providers_title": {
        "es": "Data Providers",
        "en": "Data Providers",
        "pt": "Data Providers",
    },
    "provider_goldrush_role": {
        "es": "Consultar presencia on-chain de la wallet",
        "en": "Query on-chain presence of the wallet",
        "pt": "Consultar presença on-chain da wallet",
    },
    "provider_rpc_role": {
        "es": "Consultar transacciones on-chain de la wallet",
        "en": "Query on-chain transactions of the wallet",
        "pt": "Consultar transações on-chain da wallet",
    },
    "provider_zerion_role": {
        "es": "Consultar portafolio de la wallet",
        "en": "Query wallet portfolio",
        "pt": "Consultar portfólio da wallet",
    },
    "provider_nsgood_role": {
        "es": "Consultar Compliance OFAC",
        "en": "Query OFAC compliance",
        "pt": "Consultar Compliance OFAC",
    },
    "provider_kleros_role": {
        "es": "Contratos curados y confirmados",
        "en": "Curated and confirmed contracts",
        "pt": "Contratos curados e confirmados",
    },
    "provider_sourcify_role": {
        "es": "Contratos con código fuente verificado",
        "en": "Contracts with verified source code",
        "pt": "Contratos com código-fonte verificado",
    },
    "provider_catalogs_role": {
        "es": "Catálogos CEX, Mixer, Airdrops, Bridges, Protocolos y Tokens",
        "en": "CEX, Mixer, Airdrop, Bridge, Protocol and Token catalogs",
        "pt": "Catálogos CEX, Mixer, Airdrops, Bridges, Protocolos e Tokens",
    },
}

# Static provider rows for the PDF Data Providers section (name/url fixed; role via UI key).
DATA_PROVIDER_ROWS: tuple[dict[str, Any], ...] = (
    {
        "links": (("Goldrush", "https://goldrush.dev/"),),
        "role_key": "provider_goldrush_role",
    },
    {
        "links": (
            ("Alchemy", "https://www.alchemy.com/"),
            ("EtherScan", "https://etherscan.io/"),
            ("BlockScout", "https://dev.blockscout.com/"),
            ("Ankr", "https://www.ankr.com/"),
        ),
        "role_key": "provider_rpc_role",
    },
    {
        "links": (("Zerion", "https://zerion.io/api/"),),
        "role_key": "provider_zerion_role",
    },
    {
        "links": (
            (
                "Nsgood",
                "https://x402.nsgoods.org/proof/vendor-sanctions-screen.html",
            ),
        ),
        "role_key": "provider_nsgood_role",
    },
    {
        "links": (("Kleros", "https://scout-app.kleros.io/home"),),
        "role_key": "provider_kleros_role",
    },
    {
        "links": (
            (
                "Sourcify",
                "https://ethereum.org/developers/tools/sourcify/",
            ),
        ),
        "role_key": "provider_sourcify_role",
    },
    {
        "links": (
            ("CoinGecko", "https://www.coingecko.com/"),
            ("DefiLlama", "https://defillama.com/"),
            ("Spellbook", "https://github.com/duneanalytics/spellbook"),
        ),
        "role_key": "provider_catalogs_role",
        "extra_label": {
            "es": "y otros proveedores públicos",
            "en": "and other public providers",
            "pt": "e outros provedores públicos",
        },
    },
)


def data_providers(lang: Lang) -> list[dict[str, Any]]:
    """Build localized Data Providers rows for the PDF template."""
    lang = lang if lang in SUPPORTED_LANGS else "es"
    rows: list[dict[str, Any]] = []
    for spec in DATA_PROVIDER_ROWS:
        links = [{"name": name, "url": url} for name, url in spec["links"]]
        extra = ""
        extra_map = spec.get("extra_label")
        if isinstance(extra_map, dict):
            extra = str(extra_map.get(lang) or extra_map.get("es") or "")
        rows.append(
            {
                "links": links,
                "role": t(str(spec["role_key"]), lang),
                "extra_label": extra,
            }
        )
    return rows


def normalize_idioma(value: Any) -> Lang:
    raw = str(value or "es").strip().lower()
    aliases = {
        "es": "es",
        "esp": "es",
        "español": "es",
        "espanol": "es",
        "spanish": "es",
        "en": "en",
        "eng": "en",
        "english": "en",
        "ingles": "en",
        "inglés": "en",
        "pt": "pt",
        "por": "pt",
        "portuguese": "pt",
        "portugues": "pt",
        "português": "pt",
    }
    lang = aliases.get(raw, "es")
    return lang if lang in SUPPORTED_LANGS else "es"


def t(key: str, lang: Lang, **fmt: Any) -> str:
    block = UI.get(key) or {}
    text = block.get(lang) or block.get("es") or key
    if fmt:
        return text.format(**fmt)
    return text


def tier_label(tier: str, lang: Lang) -> str:
    block = TIER_LABELS.get(tier) or {}
    return block.get(lang) or block.get("es") or tier


def module_name(key: str, lang: Lang) -> str:
    block = MODULE_NAMES.get(key) or {}
    return block.get(lang) or block.get("es") or key


def signal_label(key: str, lang: Lang) -> str:
    block = SIGNAL_LABELS.get(key)
    if not block:
        # Catalog miss: still avoid snake_case in output; use a spaced title without underscores.
        spaced = key.replace("_", " ").strip()
        return spaced
    return block.get(lang) or block.get("es") or key


def bool_text(value: bool, lang: Lang) -> str:
    return t("yes", lang) if value else t("no", lang)
