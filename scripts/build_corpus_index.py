"""Write data/corpus_index.json - a small id -> {split, sub_area, domain} map.

The full dataset/ folder (multi-GB of JSON + PDFs) is excluded from the Cloud
Foundry droplet, so the deployed backend can't tell that a paper loaded into
HANA belongs to the train or test split. This tiny index (~150 KB) IS shipped,
so /api/papers can still tag those rows 'train' / 'test' and show their sub-area.

Run it whenever the dataset/ splits change, and commit the result.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.datasets.library import CORPUS_INDEX_PATH, write_corpus_index

if __name__ == "__main__":
    count = write_corpus_index()
    size_kb = CORPUS_INDEX_PATH.stat().st_size / 1024
    print(f"wrote {count} entries to {CORPUS_INDEX_PATH} ({size_kb:.0f} KB)")
