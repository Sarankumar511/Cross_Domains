from __future__ import annotations

import random
from collections import defaultdict
from typing import Callable, Iterable

from bridgescout.datasets.schema import DatasetRecord


def stratified_split(
    records: Iterable[DatasetRecord],
    test_ratio: float = 0.2,
    seed: int = 42,
    stratify_key: Callable[[DatasetRecord], str] | None = None,
) -> tuple[list[DatasetRecord], list[DatasetRecord]]:
    """Split ``records`` into (train, test), stratified by disease sub-area.

    Deterministic for a given ``seed``. Each stratum keeps at least one record in
    train and, when it has two or more records, at least one in test — so a small
    area never lands entirely on one side. Also stamps ``record.split``.
    """
    if not 0.0 < test_ratio < 1.0:
        raise ValueError(f"test_ratio must be in (0, 1), got {test_ratio}")

    key = stratify_key or (lambda r: r.sub_area)
    rng = random.Random(seed)

    buckets: dict[str, list[DatasetRecord]] = defaultdict(list)
    for record in records:
        buckets[key(record)].append(record)

    train: list[DatasetRecord] = []
    test: list[DatasetRecord] = []
    for stratum in sorted(buckets):
        items = list(buckets[stratum])
        rng.shuffle(items)
        n_test = round(len(items) * test_ratio)
        if len(items) >= 2:
            n_test = min(max(n_test, 1), len(items) - 1)
        else:
            n_test = 0
        test.extend(items[:n_test])
        train.extend(items[n_test:])

    for record in train:
        record.split = "train"
    for record in test:
        record.split = "test"
    return train, test
