"""Parse OFAC SDN Advanced XML for Digital Currency Address entries."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"
DCA_PREFIX = "Digital Currency Address - "

ASSET_BLOCKCHAIN: dict[str, str] = {
    "XBT": "bitcoin",
    "ETH": "evm",
    "ETC": "evm",
    "BNB": "evm",
    "BSC": "evm",
    "ARB": "evm",
    "XMR": "monero",
    "LTC": "litecoin",
    "ZEC": "zcash",
    "DASH": "dash",
    "BTG": "bitcoin_gold",
    "BSV": "bitcoin_sv",
    "BCH": "bitcoin_cash",
    "XVG": "verge",
    "XRP": "ripple",
    "TRX": "tron",
    "DOGE": "dogecoin",
    "SOL": "solana",
}


def _q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _local_tag(tag: str) -> str:
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def infer_blockchain(asset_symbol: str, address: str) -> str:
    symbol = asset_symbol.upper()
    addr = address.strip()
    if symbol in ("USDT", "USDC"):
        if addr.lower().startswith("0x"):
            return "evm"
        if addr.startswith("T") and len(addr) >= 30:
            return "tron"
        return "unknown"
    mapped = ASSET_BLOCKCHAIN.get(symbol)
    if mapped:
        return mapped
    return "unknown"


def _parse_list_updated_at_el(doi: ET.Element) -> date | None:
    y = _text(doi.find(_q("Year")))
    m = _text(doi.find(_q("Month")))
    d = _text(doi.find(_q("Day")))
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return None
    return date(int(y), int(m), int(d))


def normalize_address(blockchain: str, address: str) -> str:
    addr = address.strip()
    if blockchain == "evm":
        if addr.lower().startswith("0x"):
            return "0x" + addr[2:].lower()
    return addr


def asset_symbol_from_feature_type(feature_type: str) -> str:
    if not feature_type.startswith(DCA_PREFIX):
        return ""
    return feature_type[len(DCA_PREFIX) :].strip().upper()


def _primary_entity_name(party: ET.Element) -> str:
    parts: list[str] = []
    for alias in party.iter(_q("Alias")):
        if alias.get("Primary") != "true" or alias.get("AliasTypeID") != "1403":
            continue
        for npv in alias.iter(_q("NamePartValue")):
            val = _text(npv)
            if val:
                parts.append(val)
        if parts:
            break
    if not parts:
        for npv in party.iter(_q("NamePartValue")):
            val = _text(npv)
            if val:
                parts.append(val)
            if len(parts) >= 4:
                break
    return " ".join(parts) if parts else "Unknown SDN entity"


def _feature_address(feature: ET.Element) -> str:
    for vd in feature.iter(_q("VersionDetail")):
        if vd.get("DetailTypeID") == "1432":
            val = _text(vd)
            if val:
                return val
    return ""


def collect_ofac_rows(
    xml_path: Path,
    *,
    feature_types: dict[str, str] | None = None,
    profile_programs: dict[str, list[str]] | None = None,
    list_updated_at: date | None = None,
) -> tuple[list[dict[str, Any]], date | None]:
    """
    Extract digital currency addresses from SDN Advanced XML.
    Returns (rows, list_updated_at).
    """
    path = Path(xml_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    if feature_types is None or profile_programs is None or list_updated_at is None:
        feature_types, profile_programs, list_updated_at = load_reference_data(path)

    row_map: dict[tuple[str, str], dict[str, Any]] = {}

    for _, party in ET.iterparse(path, events=("end",)):
        if _local_tag(party.tag) != "DistinctParty":
            continue

        entity_uid = (party.get("FixedRef") or "").strip()
        entity_name = _primary_entity_name(party)
        profile_id = entity_uid
        for profile in party.findall(_q("Profile")):
            pid = profile.get("ID")
            if pid:
                profile_id = pid
                break
        programs = profile_programs.get(profile_id, profile_programs.get(entity_uid, []))

        for feature in party.iter(_q("Feature")):
            ftid = feature.get("FeatureTypeID")
            if not ftid or ftid not in feature_types:
                continue
            feature_type = feature_types[ftid]
            raw_address = _feature_address(feature)
            if not raw_address:
                continue
            asset_symbol = asset_symbol_from_feature_type(feature_type)
            if not asset_symbol:
                continue
            blockchain = infer_blockchain(asset_symbol, raw_address)
            address = normalize_address(blockchain, raw_address)
            key = (blockchain, address)
            if key in row_map:
                continue
            row_map[key] = {
                "blockchain": blockchain,
                "address": address,
                "asset_symbol": asset_symbol,
                "entity_name": entity_name,
                "entity_uid": entity_uid or profile_id,
                "programs": programs,
                "feature_type": feature_type,
            }

        party.clear()

    return list(row_map.values()), list_updated_at


def _parse_sanctions_entry(entry: ET.Element) -> tuple[str, list[str]] | None:
    profile_id = entry.get("ProfileID") or entry.get("ID")
    if not profile_id:
        return None
    programs: list[str] = []
    for measure in entry.iter(_q("SanctionsMeasure")):
        comment = _text(measure.find(_q("Comment")))
        if comment:
            programs.append(comment)
    if not programs:
        return None
    return profile_id, sorted(set(programs))


_SKIP_CLEAR_TAGS = frozenset({"Year", "Month", "Day", "Comment", "SanctionsMeasure", "SanctionsEntry"})


def load_reference_data(xml_path: Path) -> tuple[dict[str, str], dict[str, list[str]], date | None]:
    """Streaming load of feature types, profile programs, and list date."""
    path = Path(xml_path)
    feature_types: dict[str, str] = {}
    profile_programs: dict[str, list[str]] = {}
    list_updated_at: date | None = None

    for _, el in ET.iterparse(path, events=("end",)):
        tag = _local_tag(el.tag)
        if tag == "FeatureType":
            label = _text(el)
            if label.startswith(DCA_PREFIX):
                fid = el.get("ID")
                if fid:
                    feature_types[fid] = label
        elif tag == "DateOfIssue" and list_updated_at is None:
            list_updated_at = _parse_list_updated_at_el(el)
        elif tag == "SanctionsEntry":
            parsed = _parse_sanctions_entry(el)
            if parsed:
                profile_programs[parsed[0]] = parsed[1]
        if tag not in _SKIP_CLEAR_TAGS:
            el.clear()

    return feature_types, profile_programs, list_updated_at
