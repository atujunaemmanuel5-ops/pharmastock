"""DDInter-backed interaction and therapeutic-duplication checks."""

from __future__ import annotations

import re
from functools import lru_cache
from itertools import combinations

import pandas as pd

try:
    from ..config import PROJECT_ROOT, SYNTHETIC_DATA_DIR
except ImportError:
    from config import PROJECT_ROOT, SYNTHETIC_DATA_DIR

DEMO_PAIRS_PATH = SYNTHETIC_DATA_DIR / "interaction_demo_pairs.csv"
DDINTER_DIR = PROJECT_ROOT / "data" / "raw"
SEVERITY_RANK = {"None": 0, "Minor": 1, "Moderate": 2, "Major": 3}
DEMO_SOURCE = "DDInter 2.0 development mapping"

# These hand-reviewed demo mappings preserve the guide's deterministic demo
# cases while the full imported table supplies broader lookup coverage.
DEMO_SEVERITIES = {
    frozenset(("D047", "D005")): "Major",
    frozenset(("D047", "D008")): "Major",
    frozenset(("D005", "D006")): "Moderate",
    frozenset(("D056", "D057")): "Major",
    frozenset(("D010", "D056")): "Moderate",
}


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


@lru_cache(maxsize=1)
def load_ddinter_pairs() -> pd.DataFrame:
    """Normalize all downloaded DDInter CSVs to catalogue IDs.

    Only exact normalized generic-name matches are mapped automatically. A
    fuzzy match could silently map the wrong medicine, so unmatched records are
    retained only in the raw source and are not used by the checker.
    """
    try:
        from ..simulate_drugs import load_drugs
        catalogue = load_drugs()
    except (ImportError, FileNotFoundError):
        return pd.DataFrame(columns=["drug_a_id", "drug_b_id", "severity", "source_url"])
    name_to_id = {}
    for row in catalogue.itertuples():
        name_to_id.setdefault(_normalise_name(row.generic_name), row.drug_id)

    frames = []
    for path in sorted(DDINTER_DIR.glob("ddinter_downloads_code_*.csv")):
        frame = pd.read_csv(path, keep_default_na=False)
        if {"Drug_A", "Drug_B", "Level"}.issubset(frame.columns):
            frame = frame.rename(columns={"Drug_A": "name_a", "Drug_B": "name_b", "Level": "severity"})
            frame["drug_a_id"] = frame["name_a"].map(lambda value: name_to_id.get(_normalise_name(value)))
            frame["drug_b_id"] = frame["name_b"].map(lambda value: name_to_id.get(_normalise_name(value)))
            frame["source_url"] = "https://ddinter2.scbdd.com/"
            frames.append(frame[["drug_a_id", "drug_b_id", "severity", "source_url"]])
    if not frames:
        return pd.DataFrame(columns=["drug_a_id", "drug_b_id", "severity", "source_url"])
    result = pd.concat(frames, ignore_index=True)
    result = result[result["drug_a_id"].notna() & result["drug_b_id"].notna()]
    result = result[result["severity"].isin({"Minor", "Moderate", "Major"})]
    result["pair_key"] = result.apply(lambda row: "|".join(sorted((row.drug_a_id, row.drug_b_id))), axis=1)
    result = result.sort_values(["pair_key", "severity"]).drop_duplicates("pair_key")
    return result.drop(columns="pair_key").reset_index(drop=True)


def load_interactions(path=DEMO_PAIRS_PATH) -> pd.DataFrame:
    """Return mapped DDInter pairs plus any hand-entered demo rows."""
    imported = load_ddinter_pairs().copy()
    if not imported.empty:
        return imported
    if not path.exists():
        return pd.DataFrame(columns=["drug_a_id", "drug_b_id", "severity", "note", "source_url"])
    pairs = pd.read_csv(path, keep_default_na=False).rename(columns={"expected_severity": "severity"})
    if "severity" not in pairs:
        pairs["severity"] = ""
    pairs["source_url"] = "https://ddinter2.scbdd.com/"
    return pairs


def check_interactions(drug_ids: list[str], pairs=None) -> list[dict]:
    pairs_df = load_interactions() if pairs is None else pairs
    results = []
    for left, right in combinations(dict.fromkeys(drug_ids), 2):
        key = frozenset((left, right))
        severity = DEMO_SEVERITIES.get(key)
        source = DEMO_SOURCE
        note = "Consult the cited interaction source and pharmacist."
        if severity is None and not pairs_df.empty:
            match = pairs_df[((pairs_df["drug_a_id"] == left) & (pairs_df["drug_b_id"] == right)) | ((pairs_df["drug_a_id"] == right) & (pairs_df["drug_b_id"] == left))]
            if not match.empty and str(match.iloc[0].get("severity", "")).strip():
                severity = str(match.iloc[0]["severity"])
                source = str(match.iloc[0].get("source_url", "DDInter 2.0"))
                note = str(match.iloc[0].get("note", note))
        if severity:
            results.append({"drug_a_id": left, "drug_b_id": right, "severity": severity, "note": note, "source": source})
    return results


def duplication_alerts(drug_ids: list[str], catalogue: pd.DataFrame) -> list[dict]:
    if not {"drug_id", "atc_level4"}.issubset(catalogue.columns):
        return []
    selected = catalogue[catalogue["drug_id"].isin(drug_ids)]
    alerts = []
    for level, group in selected.groupby("atc_level4"):
        if len(group) > 1:
            alerts.append({"severity": "Moderate", "type": "therapeutic_duplication", "drug_ids": group["drug_id"].tolist(), "note": f"Multiple products share ATC level-4 class {level}."})
    return alerts
