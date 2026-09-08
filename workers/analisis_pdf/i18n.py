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
    "kleros_tagged_contract_pct": {
        "es": "Contratos etiquetados Kleros",
        "en": "Kleros-tagged contracts",
        "pt": "Contratos etiquetados Kleros",
    },
    "cex_deposit_inferred_pct": {
        "es": "Depósito CEX inferido (% valor)",
        "en": "Inferred CEX deposit (% value)",
        "pt": "Depósito CEX inferido (% valor)",
    },
    "cex_curated_pct": {
        "es": "CEX etiquetado Spellbook (% valor)",
        "en": "Spellbook-labeled CEX (% value)",
        "pt": "CEX etiquetado Spellbook (% valor)",
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
    "custody_title": {
        "es": "Clasificación de custodia",
        "en": "Custody classification",
        "pt": "Classificação de custódia",
    },
    "custody_class": {
        "es": "Clase",
        "en": "Class",
        "pt": "Classe",
    },
    "custody_p_hosted": {
        "es": "Prob. hosted",
        "en": "Hosted probability",
        "pt": "Prob. hosted",
    },
    "custody_p_unhosted": {
        "es": "Prob. unhosted",
        "en": "Unhosted probability",
        "pt": "Prob. unhosted",
    },
    "custody_p_unknown": {
        "es": "Prob. desconocida",
        "en": "Unknown probability",
        "pt": "Prob. desconhecida",
    },
    "custody_confidence": {
        "es": "Confianza",
        "en": "Confidence",
        "pt": "Confiança",
    },
    "custody_cex_name": {
        "es": "CEX (catálogo)",
        "en": "CEX (catalog)",
        "pt": "CEX (catálogo)",
    },
    "custody_wallet_role": {
        "es": "Rol de wallet",
        "en": "Wallet role",
        "pt": "Papel da wallet",
    },
    "custody_evidence": {
        "es": "Evidencia",
        "en": "Evidence",
        "pt": "Evidência",
    },
    "custody_disclaimer": {
        "es": (
            "Señal on-chain probabilística sobre el tipo de custodia aparente del sujeto. "
            "No prueba control de claves ni sustituye debida diligencia del receptor."
        ),
        "en": (
            "Probabilistic on-chain signal about the subject's apparent custody type. "
            "It does not prove key control or replace the recipient's due diligence."
        ),
        "pt": (
            "Sinal on-chain probabilístico sobre o tipo aparente de custódia do sujeito. "
            "Não prova controle de chaves nem substitui a devida diligência do receptor."
        ),
    },
    "clusters_title": {
        "es": "Origen por clase de entidad",
        "en": "Origin by entity class",
        "pt": "Origem por classe de entidade",
    },
    "clusters_col_class": {
        "es": "Clase",
        "en": "Class",
        "pt": "Classe",
    },
    "clusters_col_pct": {
        "es": "% valor",
        "en": "% value",
        "pt": "% valor",
    },
    "clusters_top_title": {
        "es": "Top orígenes etiquetados",
        "en": "Top labeled origins",
        "pt": "Top origens etiquetadas",
    },
    "clusters_col_address": {
        "es": "Address",
        "en": "Address",
        "pt": "Address",
    },
    "clusters_col_label": {
        "es": "Etiqueta",
        "en": "Label",
        "pt": "Etiqueta",
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
        "es": "Hops / screening de fondeadores",
        "en": "Hops / funder risk screening",
        "pt": "Hops / screening de financiadores",
    },
    "origins_hops_blurb": {
        "es": "Screening de riesgo de los principales fondeadores (OFAC, mixer, CEX, bridge). Contexto de quién fondeó al sujeto — no es un re-análisis Origins completo.",
        "en": "Risk screening of top funders (OFAC, mixer, CEX, bridge). Context on who funded the subject — not a full Origins re-analysis.",
        "pt": "Screening de risco dos principais financiadores (OFAC, mixer, CEX, bridge). Contexto de quem financiou o sujeito — não é uma reanálise Origins completa.",
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
    "hop_funder_summary": {
        "es": "Screening de fondeador (nota {grade}): {exposure}. Categoría {category}.",
        "en": "Funder risk screening (grade {grade}): {exposure}. Category {category}.",
        "pt": "Screening de financiador (nota {grade}): {exposure}. Categoria {category}.",
    },
    "hop_funder_clean": {
        "es": "sin señales OFAC / mixer / CEX / bridge",
        "en": "no OFAC / mixer / CEX / bridge signals",
        "pt": "sem sinais OFAC / mixer / CEX / bridge",
    },
    "hop_funder_hits": {
        "es": "señales {hits}",
        "en": "signals {hits}",
        "pt": "sinais {hits}",
    },
    "hop_flag_ofac": {"es": "OFAC", "en": "OFAC", "pt": "OFAC"},
    "hop_flag_mixer": {"es": "Mixer", "en": "Mixer", "pt": "Mixer"},
    "hop_flag_cex": {"es": "CEX", "en": "CEX", "pt": "CEX"},
    "hop_flag_cex_named": {
        "es": "CEX ({name})",
        "en": "CEX ({name})",
        "pt": "CEX ({name})",
    },
    "hop_flag_bridge": {"es": "Bridge", "en": "Bridge", "pt": "Bridge"},
    "hop_flag_bool": {
        "es": "{name}: {value}",
        "en": "{name}: {value}",
        "pt": "{name}: {value}",
    },
    "hop_flag_bool_detail": {
        "es": "{name}: {value} ({detail})",
        "en": "{name}: {value} ({detail})",
        "pt": "{name}: {value} ({detail})",
    },
    "hop_flags_legend": {
        "es": "Señales del fondeador (sí/no)",
        "en": "Funder signals (yes/no)",
        "pt": "Sinais do financiador (sim/não)",
    },
    "hop_error": {
        "es": "Screening no disponible ({error}).",
        "en": "Screening unavailable ({error}).",
        "pt": "Screening indisponível ({error}).",
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
    "hop_excluded": {
        "es": "Wallet excluida ({reason}).",
        "en": "Wallet excluded ({reason}).",
        "pt": "Carteira excluída ({reason}).",
    },
    "hop_excluded_cex": {
        "es": "Wallet excluida ({reason}): {cex_name}.",
        "en": "Wallet excluded ({reason}): {cex_name}.",
        "pt": "Carteira excluída ({reason}): {cex_name}.",
    },
    "skip_reason_cex_label": {
        "es": "etiqueta CEX",
        "en": "CEX label",
        "pt": "etiqueta CEX",
    },
    "skip_reason_cex_catalog": {
        "es": "catálogo CEX",
        "en": "CEX catalog",
        "pt": "catálogo CEX",
    },
    "skip_reason_zero_address": {
        "es": "dirección cero",
        "en": "zero address",
        "pt": "endereço zero",
    },
    "skip_reason_subject": {
        "es": "wallet sujeto",
        "en": "subject wallet",
        "pt": "carteira sujeito",
    },
    "skip_reason_bridge_label": {
        "es": "etiqueta bridge",
        "en": "bridge label",
        "pt": "etiqueta bridge",
    },
    "skip_reason_mixer_label": {
        "es": "etiqueta mixer",
        "en": "mixer label",
        "pt": "etiqueta mixer",
    },
    "skip_reason_ofac_label": {
        "es": "etiqueta OFAC",
        "en": "OFAC label",
        "pt": "etiqueta OFAC",
    },
    "skip_reason_skipped": {
        "es": "excluida",
        "en": "excluded",
        "pt": "excluída",
    },
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


CUSTODY_CLASS_LABELS: dict[str, dict[str, str]] = {
    "hosted_known": {
        "es": "Hosted conocido (catálogo CEX)",
        "en": "Known hosted (CEX catalog)",
        "pt": "Hosted conhecido (catálogo CEX)",
    },
    "hosted_deposit_inferred": {
        "es": "Hosted — depósito inferido",
        "en": "Hosted — inferred deposit",
        "pt": "Hosted — depósito inferido",
    },
    "likely_unhosted": {
        "es": "Probablemente unhosted",
        "en": "Likely unhosted",
        "pt": "Provavelmente unhosted",
    },
    "unknown": {
        "es": "Desconocido",
        "en": "Unknown",
        "pt": "Desconhecido",
    },
}

CONFIDENCE_LABELS: dict[str, dict[str, str]] = {
    "low": {"es": "Baja", "en": "Low", "pt": "Baixa"},
    "medium": {"es": "Media", "en": "Medium", "pt": "Média"},
    "high": {"es": "Alta", "en": "High", "pt": "Alta"},
}

ENTITY_CLASS_LABELS: dict[str, dict[str, str]] = {
    "exchange_vasp": {
        "es": "Exchange / VASP etiquetado",
        "en": "Labeled exchange / VASP",
        "pt": "Exchange / VASP etiquetado",
    },
    "exchange_deposit_inferred": {
        "es": "Depósito CEX inferido",
        "en": "Inferred CEX deposit",
        "pt": "Depósito CEX inferido",
    },
    "defi_protocol": {
        "es": "Protocolo DeFi",
        "en": "DeFi protocol",
        "pt": "Protocolo DeFi",
    },
    "mixer": {"es": "Mixer", "en": "Mixer", "pt": "Mixer"},
    "sanctioned": {
        "es": "Exposición sancionada (señal)",
        "en": "Sanctioned exposure (signal)",
        "pt": "Exposição sancionada (sinal)",
    },
    "bridge": {"es": "Bridge", "en": "Bridge", "pt": "Bridge"},
    "airdrop": {"es": "Airdrop", "en": "Airdrop", "pt": "Airdrop"},
    "unlabeled": {
        "es": "Sin etiqueta",
        "en": "Unlabeled",
        "pt": "Sem etiqueta",
    },
    # funder_risk entity_class / primary_category aliases
    "exchange": {"es": "Exchange / CEX", "en": "Exchange / CEX", "pt": "Exchange / CEX"},
    "protocol": {"es": "Protocolo", "en": "Protocol", "pt": "Protocolo"},
    "organic": {"es": "Orgánico", "en": "Organic", "pt": "Orgânico"},
    "cex": {"es": "CEX", "en": "CEX", "pt": "CEX"},
    "cex_deposit_inferred": {
        "es": "Depósito CEX inferido",
        "en": "Inferred CEX deposit",
        "pt": "Depósito CEX inferido",
    },
    "ofac": {
        "es": "Exposición sancionada (señal)",
        "en": "Sanctioned exposure (signal)",
        "pt": "Exposição sancionada (sinal)",
    },
}

ENTITY_CLASS_ORDER = (
    "exchange_vasp",
    "exchange_deposit_inferred",
    "defi_protocol",
    "mixer",
    "sanctioned",
    "bridge",
    "airdrop",
    "unlabeled",
)


def custody_class_label(class_key: str, lang: Lang) -> str:
    block = CUSTODY_CLASS_LABELS.get(class_key) or {}
    return block.get(lang) or block.get("es") or class_key.replace("_", " ")


def confidence_label(key: str, lang: Lang) -> str:
    block = CONFIDENCE_LABELS.get(key) or {}
    return block.get(lang) or block.get("es") or key


def entity_class_label(class_key: str, lang: Lang) -> str:
    block = ENTITY_CLASS_LABELS.get(class_key) or {}
    return block.get(lang) or block.get("es") or class_key.replace("_", " ")


def skip_reason_label(reason: str, lang: Lang) -> str:
    """Human-readable skip_reason for PDF hops/lights (es|en|pt)."""
    code = str(reason or "skipped").strip().lower() or "skipped"
    key = f"skip_reason_{code}"
    if key in UI:
        return t(key, lang)
    if code.endswith("_label"):
        base = code[: -len("_label")]
        mapped = {
            "cex": "skip_reason_cex_label",
            "bridge": "skip_reason_bridge_label",
            "mixer": "skip_reason_mixer_label",
            "ofac": "skip_reason_ofac_label",
        }.get(base)
        if mapped and mapped in UI:
            return t(mapped, lang)
    return code.replace("_", " ")
