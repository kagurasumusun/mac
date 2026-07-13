from __future__ import annotations

import argparse
from pathlib import Path
import sys
import json

from .compiler import CompileOptions, compile_catalogs

VERSION = "actool-linux 0.1.0 (clean-room compatibility layer)"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="actool", allow_abbrev=False)
    p.add_argument("inputs", nargs="*", type=Path)
    p.add_argument("--compile", dest="output", type=Path)
    p.add_argument("--platform")
    p.add_argument("--minimum-deployment-target")
    p.add_argument("--app-icon")
    p.add_argument("--accent-color")
    p.add_argument("--launch-image")
    p.add_argument("--output-partial-info-plist", type=Path)
    # Apple exposes these as valueless switches. A following "no" is an input
    # path, not a boolean value (verified by the option cross-product oracle).
    p.add_argument("--warnings", action="store_true", default=True)
    p.add_argument("--errors", action="store_true", default=True)
    p.add_argument("--notices", action="store_true", default=True)
    p.add_argument("--target-device", action="append", choices=("iphone","ipad","tv","watch","mac","vision"), default=[])
    p.add_argument("--filter-for-device-model")
    p.add_argument("--filter-for-device-os-version")
    p.add_argument("--product-type")
    p.add_argument("--development-region")
    p.add_argument("--compress-pngs", action="store_true", default=True)
    p.add_argument("--enable-on-demand-resources", choices=("yes","no"), default="no")
    p.add_argument("--print-contents", action="store_true")
    # Apple's current actool emits an XML result plist when the option is
    # omitted. Human-readable output is only selected explicitly.
    p.add_argument("--output-format", choices=("human-readable-text","xml1"), default="xml1")
    p.add_argument("--version", action="store_true")
    p.add_argument("--compatibility-xcode-version", choices=("16.0","16.1","16.2","16.3","16.4","26.0.1","26.1.1","26.2","26.3","26.4.1","26.5","26.6"), default="26.5")
    p.add_argument("--capabilities", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    ns, unknown = parser().parse_known_args(args)
    # argparse can leave interspersed positional inputs behind after valueless
    # switches. Apple treats those tokens as input documents, not options.
    positional_unknown = [item for item in unknown if not item.startswith("-")]
    ns.inputs.extend(Path(item) for item in positional_unknown)
    unknown = [item for item in unknown if item.startswith("-")]
    if unknown:
        from .diagnostics import unknown_argument_plist
        sys.stdout.buffer.write(unknown_argument_plist(unknown[0], include_missing_input="--compile" in args))
        return 1
    if ns.version:
        if ns.output_format == "xml1":
            from .diagnostics import version_plist
            sys.stdout.buffer.write(version_plist(short_version=ns.compatibility_xcode_version))
        else:
            print(VERSION)
        return 0
    if ns.capabilities:
        from .capabilities import capability_report
        print(json.dumps(capability_report(), indent=2, ensure_ascii=False))
        return 0
    if ns.output is None:
        print("actool: error: --compile is required", file=sys.stderr)
        return 1
    resolved_inputs = list(dict.fromkeys(path.resolve() for path in ns.inputs))
    result = compile_catalogs(resolved_inputs, CompileOptions(
        output=ns.output,
        platform=ns.platform,
        minimum_deployment_target=ns.minimum_deployment_target,
        app_icon=ns.app_icon,
        accent_color=ns.accent_color,
        launch_image=ns.launch_image,
        partial_info_plist=ns.output_partial_info_plist,
        warnings=ns.warnings,
        errors=ns.errors,
        notices=ns.notices,
        target_devices=tuple(ns.target_device),
        filter_for_device_model=ns.filter_for_device_model,
        filter_for_device_os_version=ns.filter_for_device_os_version,
        product_type=ns.product_type,
        development_region=ns.development_region,
        compress_pngs=ns.compress_pngs,
        enable_on_demand_resources=ns.enable_on_demand_resources == "yes",
    ))
    visible = []
    for diagnostic in result.diagnostics:
        enabled = {
            "warning": ns.warnings, "error": ns.errors, "notice": ns.notices,
        }.get(diagnostic.severity, True)
        if enabled: visible.append(diagnostic)
    if ns.output_format == "xml1":
        from .diagnostics import result_plist
        include_results = bool(resolved_inputs) and any(path.exists() for path in resolved_inputs) and not (ns.app_icon and ns.output_partial_info_plist is None)
        sys.stdout.buffer.write(result_plist(visible, result.outputs, include_compilation_results=include_results))
    else:
        for diagnostic in visible: print(diagnostic.render(), file=sys.stderr)
        if ns.print_contents:
            for output in result.outputs: print(output)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
