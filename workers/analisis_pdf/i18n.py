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
    "footer_note": {
        "es": (
            "Vista derivada del JSON analisis-v1. Walpulse produce señales on-chain; "
            "el receptor interpreta. No es decisión de compliance ni screening oficial."
        ),
        "en": (
            "Derived view of analisis-v1 JSON. Walpulse produces on-chain signals; "
            "the recipient interprets them. Not a compliance decision or official screening."
        ),
        "pt": (
            "Vista derivada do JSON analisis-v1. Walpulse produz sinais on-chain; "
            "o receptor interpreta. Não é decisão de compliance nem screening oficial."
        ),
    },
}


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
