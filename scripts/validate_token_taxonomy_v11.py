"""One-off validation: collect token_taxonomy rows and print counts (no Supabase)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from workers.token_taxonomy.defillama import SPARSE_PATH
from workers.token_taxonomy.job import get_git_commit, sparse_clone_peggedassets
from workers.token_taxonomy.parse import collect_token_taxonomy_rows


def main() -> int:
    api_key = (os.environ.get("COINGECKO_KEY") or "").strip()
    if not api_key:
        print("SKIP: set COINGECKO_KEY for live validation")
        return 0

    tmpdir = Path(tempfile.mkdtemp(prefix="taxonomy-validate-"))
    try:
        repo = sparse_clone_peggedassets(tmpdir)
        commit = get_git_commit(repo)
        rows, source_hash, stats = collect_token_taxonomy_rows(
            api_key,
            adapters_root=repo / SPARSE_PATH,
            defillama_commit=commit,
        )
        stable = sum(1 for r in rows if "stable" in r.get("categories", []))
        print(f"rows={len(rows)} stable={stable} hash={source_hash[:16]}")
        print(
            f"dl_stable_rows={stats.get('dl_stable_rows')} "
            f"git_rows={stats.get('git_rows')} gap_rows={stats.get('gap_rows')}"
        )
        if len(rows) < 3800:
            print("WARN: rows below 3800 target")
            return 1
        if stable < 1100:
            print("WARN: stable below 1100 target")
            return 1
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
