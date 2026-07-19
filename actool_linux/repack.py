from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .bom import BOMError, BOMStore
from .bomwriter import BOMWriter


def repack(source: Path, destination: Path) -> None:
    store = BOMStore.from_path(source)
    identifiers = sorted(store.blocks)
    expected = list(range(1, max(identifiers, default=0) + 1))
    if identifiers != expected:
        raise BOMError("cannot repack a sparse block index without preserving explicit identifiers")
    names_by_id: dict[int, str] = {}
    for name, identifier in store.variables.items():
        if identifier in names_by_id:
            raise BOMError(f"block {identifier} has multiple variable names")
        names_by_id[identifier] = name
    writer = BOMWriter()
    for identifier in identifiers:
        assigned = writer.add_block(bytes(store.block(identifier)), names_by_id.get(identifier))
        if assigned != identifier:
            raise AssertionError("BOM writer changed a referenced block identifier")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(writer.build())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="actool-car-repack")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    ns = parser.parse_args(argv)
    try:
        repack(ns.source, ns.destination)
    except (OSError, BOMError) as exc:
        print(f"actool-car-repack: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
