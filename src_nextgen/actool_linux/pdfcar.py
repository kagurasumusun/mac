from __future__ import annotations
import argparse
from pathlib import Path
import sys
from .carwriter import build_pdf_fallback_car


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='actool-pdf-car', description='Build PDF vector CAR with GA8 1x/2x deepmap fallbacks')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--name', required=True)
    p.add_argument('--pdf', required=True, type=Path)
    p.add_argument('--fallback-1x', required=True, type=Path)
    p.add_argument('--fallback-2x', required=True, type=Path)
    p.add_argument('--fallback-3x', type=Path)
    p.add_argument('--platform', default='macosx')
    p.add_argument('--target', default='13.0')
    ns = p.parse_args(argv)
    try:
        raw = build_pdf_fallback_car(ns.name, ns.pdf.read_bytes(), ns.fallback_1x.read_bytes(), ns.fallback_2x.read_bytes(
        ), ns.pdf.name, png_3x=ns.fallback_3x.read_bytes() if ns.fallback_3x else None, platform=ns.platform, target=ns.target)
        ns.output.parent.mkdir(parents=True, exist_ok=True)
        ns.output.write_bytes(raw)
    except (OSError, ValueError) as exc:
        print(f'actool-pdf-car: error: {exc}', file=sys.stderr)
        return 1
    print(ns.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
