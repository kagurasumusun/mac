from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import plistlib

from .carwriter import (
    app_icon_renditions, build_assets_car, color_rendition, data_rendition,
    heif_rendition, jpeg_rendition, layered_image_renditions, png_rendition, resize_png, svg_renditions, symbol_rendition, png_dimensions,
)
from .model import Catalog, Diagnostic, load_catalog
from .appicons import app_icon_sidecar_specs


@dataclass
class CompileOptions:
    output: Path
    platform: str | None = None
    minimum_deployment_target: str | None = None
    app_icon: str | None = None
    accent_color: str | None = None
    launch_image: str | None = None
    partial_info_plist: Path | None = None
    warnings: bool = True
    errors: bool = True
    notices: bool = True
    target_devices: tuple[str, ...] = ()
    filter_for_device_model: str | None = None
    filter_for_device_os_version: str | None = None
    product_type: str | None = None
    development_region: str | None = None
    compress_pngs: bool = True
    enable_on_demand_resources: bool = False


@dataclass
class CompileResult:
    catalogs: list[Catalog]
    diagnostics: list[Diagnostic]
    outputs: list[Path]

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)


def _partial_info(catalogs: Iterable[Catalog], options: CompileOptions) -> dict[str, object]:
    result: dict[str, object] = {}
    names = {asset.name for catalog in catalogs for asset in catalog.assets}
    if options.app_icon and options.app_icon in names:
        primary = {
            "CFBundleIconFiles": ["AppIcon60x60"],
            "CFBundleIconName": options.app_icon,
        }
        result["CFBundleIcons"] = {"CFBundlePrimaryIcon": primary}
        if (options.platform or "").lower() in ("iphoneos", "iphonesimulator", "ios"):
            result["CFBundleIcons~ipad"] = {
                "CFBundlePrimaryIcon": {
                    "CFBundleIconFiles": ["AppIcon60x60", "AppIcon76x76"],
                    "CFBundleIconName": options.app_icon,
                }
            }
    return result


def compile_catalogs(inputs: list[Path], options: CompileOptions) -> CompileResult:
    catalogs = [load_catalog(path) for path in inputs]
    diagnostics = [item for catalog in catalogs for item in catalog.diagnostics]
    outputs: list[Path] = []

    # Apple treats malformed per-asset Contents.json as a notice and emits an
    # empty compilation-results array rather than failing the invocation.
    normalized: list[Diagnostic] = []
    for diagnostic in diagnostics:
        if diagnostic.path is not None and diagnostic.path.name == "Contents.json" and diagnostic.message.startswith("cannot read Contents.json:"):
            normalized.append(Diagnostic("notice", f'The Contents.json describing the "{diagnostic.path.parent.name}" is not valid JSON.'))
        elif diagnostic.path is not None and diagnostic.path.name == "Contents.json" and diagnostic.message == "Contents.json root must be an object":
            normalized.append(Diagnostic("notice", f'The Contents.json describing "{diagnostic.path.parent.name}" must start with a top level dictionary.'))
        elif diagnostic.message in ("'images' must be an array", "'images' contains a non-object entry", "Contents.json has no complete info dictionary"):
            # Xcode silently ignores these schema defects in image sets.
            continue
        else:
            normalized.append(diagnostic)
    diagnostics = [d for d in normalized if not (d.severity == "warning" and d.message.startswith("referenced file is missing:"))]

    if not inputs:
        diagnostics.append(Diagnostic("error", "Not enough arguments provided; where is the input document to operate on?"))
    else:
        missing = [path for path in inputs if not path.exists()]
        if missing:
            diagnostics = [d for d in diagnostics if d.path not in missing]
            diagnostics.extend(Diagnostic("notice", f'Failed to read file attributes for "{path}"', failure_reason="No such file or directory") for path in missing)
            if not options.minimum_deployment_target:
                diagnostics.append(Diagnostic("notice", 'Compiling requires passing "--minimum-deployment-target [value]".'))
            if not options.platform:
                diagnostics.append(Diagnostic("notice", 'Compiling requires passing "--platform [platform-name]".'))
            return CompileResult(catalogs, diagnostics, outputs)
    if any(d.severity == "notice" and d.message.startswith("The Contents.json describing") for d in diagnostics):
        return CompileResult(catalogs, diagnostics, outputs)

    if options.app_icon and any(asset.kind == "app-icon" and asset.name == options.app_icon for catalog in catalogs for asset in catalog.assets) and options.partial_info_plist is None:
        diagnostics.append(Diagnostic("notice", 'Compiling app icons requires passing "--output-partial-info-plist [path]".'))
        return CompileResult(catalogs, diagnostics, outputs)
    missing_app_icon = bool(options.app_icon) and not any(
        asset.kind == "app-icon" and asset.name == options.app_icon
        for catalog in catalogs for asset in catalog.assets
    )
    # Xcode still compiles unrelated assets and writes the partial plist before
    # reporting a requested-but-absent AppIcon as an error.  Defer this error
    # until output production is complete so compilation-results stay intact.
    missing_launch_image = bool(options.launch_image) and not any(
        asset.kind == "launch-image" and asset.name == options.launch_image
        for catalog in catalogs for asset in catalog.assets
    )
    if (options.platform or "").lower() in ("appletvos","appletvsimulator","xros","xrsimulator") and options.filter_for_device_model and options.filter_for_device_os_version:
        diagnostics.append(Diagnostic("notice", f"Could not get trait set for device {options.filter_for_device_model} with version {options.filter_for_device_os_version}"))

    deferred_partial_info: Path | None = None
    if not any(item.severity == "error" for item in diagnostics):
        options.output.mkdir(parents=True, exist_ok=True)
        if options.partial_info_plist:
            options.partial_info_plist.parent.mkdir(parents=True, exist_ok=True)
            with options.partial_info_plist.open("wb") as stream:
                plistlib.dump(_partial_info(catalogs, options), stream, fmt=plistlib.FMT_BINARY)
            # actool lists primary compiled products before this auxiliary plist.
            deferred_partial_info = options.partial_info_plist

        assets = [asset for catalog in catalogs for asset in catalog.assets]
        renditions = []
        occupied_slots: set[tuple[object, ...]] = set()
        app_icon_emitted: set[str] = set()
        known_idioms = {"universal","iphone","ipad","tv","watch","mac","vision","car","marketing"}

        def appearance_for(entry: dict[str, object]) -> str:
            result = "any"
            appearances = entry.get("appearances", [])
            if not isinstance(appearances, list):
                return result
            for item in appearances:
                if not isinstance(item, dict):
                    continue
                kind, value = item.get("appearance"), item.get("value")
                if kind == "luminosity" and value == "dark": result = "dark"
                elif kind == "contrast" and value == "high": result = "high-contrast"
            return result

        for asset in assets:
            if asset.kind == "image-stack":
                layer_bytes: list[bytes] = []
                stack_scale = 1
                for layer_ref in asset.entries:
                    dirname = layer_ref.get("filename")
                    if not isinstance(dirname, str): continue
                    layer_dir = asset.directory / dirname
                    layer_asset = next((candidate for candidate in assets if candidate.kind == "image-stack-layer" and candidate.directory == layer_dir), None)
                    if layer_asset is None: continue
                    selected = next((entry for entry in layer_asset.entries if isinstance(entry.get("filename"), str) and (layer_dir / str(entry["filename"])).is_file()), None)
                    if selected is None: continue
                    scale_text = str(selected.get("scale", "1x"))
                    if scale_text in ("1x", "2x", "3x"): stack_scale = int(scale_text[0])
                    layer_bytes.append((layer_dir / str(selected["filename"])).read_bytes())
                if layer_bytes:
                    platform = (options.platform or "appletvos").lower()
                    idiom = "vision" if platform in ("xros", "xrsimulator", "visionos") else "tv"
                    try: renditions.extend(layered_image_renditions(asset.name, layer_bytes, idiom=idiom, scale=stack_scale))
                    except ValueError as exc: diagnostics.append(Diagnostic("error", f"invalid image stack: {exc}", asset.directory))
                continue
            if asset.kind in ("image-stack-layer", "brand-assets"):
                continue

            # Real AppIcon catalogs commonly contain many legacy sizes.  Select
            # the largest dimension-applicable source (normally the modern
            # 1024x1024 marketing slot) instead of whichever entry appears first.
            if asset.kind == "app-icon":
                if options.app_icon != asset.name:
                    continue
                candidates: list[tuple[int, bytes, str]] = []
                for icon_entry in asset.entries:
                    filename = icon_entry.get("filename")
                    if not isinstance(filename, str): continue
                    source = asset.directory / filename
                    if not source.is_file(): continue
                    try:
                        source_png = source.read_bytes(); actual = png_dimensions(source_png)
                        declared = str(icon_entry.get("size", "")); scale_text = str(icon_entry.get("scale", "1x"))
                        if declared:
                            points = declared.split("x", 1); scale = int(scale_text[:-1]) if scale_text.endswith("x") else 1
                            expected = (round(float(points[0]) * scale), round(float(points[1]) * scale))
                            if actual != expected: continue
                        candidates.append((actual[0] * actual[1], source_png, filename))
                    except ValueError:
                        continue
                if candidates:
                    _, source_png, filename = max(candidates, key=lambda row: row[0])
                    try:
                        renditions.extend(app_icon_renditions(asset.name, source_png, filename,
                                                             platform=options.platform or "iphoneos"))
                        for sidecar_name, width, height in app_icon_sidecar_specs(options.platform or "iphoneos"):
                            sidecar = options.output / sidecar_name
                            sidecar.write_bytes(resize_png(source_png, width, height)); outputs.append(sidecar)
                        app_icon_emitted.add(asset.name)
                    except ValueError as exc:
                        diagnostics.append(Diagnostic("error", f"invalid AppIcon: {exc}", asset.directory))
                continue

            # Empty placeholder sets and unassigned slots are legal in genuine
            # catalogs.  Iterate every assigned entry rather than enforcing the
            # old single-entry development restriction.
            for entry in asset.entries:
                idiom = str(entry.get("idiom", "universal"))
                if idiom not in known_idioms:
                    continue
                scale_text = str(entry.get("scale", "1x"))
                if asset.kind in ("image", "symbol") and scale_text not in ("1x", "2x", "3x"):
                    continue
                scale_value = int(scale_text[0]) if scale_text in ("1x", "2x", "3x") else 1
                appearance = appearance_for(entry)
                localization = entry.get("locale")
                localization = str(localization) if isinstance(localization, str) and localization else None
                slot = (asset.kind, asset.name, idiom, scale_value, appearance, localization,
                        entry.get("subtype"), entry.get("role"))
                if slot in occupied_slots:
                    # Xcode accepts duplicate slots.  Controlled probes show a
                    # deterministic winner; preserve Contents.json order and
                    # retain the first assigned slot.
                    continue

                if asset.kind == "color":
                    try:
                        color = entry["color"]
                        color_space = str(color.get("color-space"))
                        if color_space not in ("srgb", "display-p3"):
                            raise ValueError("only sRGB and Display P3 colors are enabled")
                        components = color["components"]
                        values = [float(components[name]) for name in ("red", "green", "blue", "alpha")]
                        renditions.append(color_rendition(asset.name, *values, color_space=color_space,
                                                          idiom=idiom, appearance=appearance))
                        occupied_slots.add(slot)
                    except (KeyError, TypeError, ValueError) as exc:
                        diagnostics.append(Diagnostic("error", f"invalid color entry: {exc}", asset.directory))
                    continue

                filename = entry.get("filename")
                if not isinstance(filename, str):
                    continue
                source = asset.directory / filename
                if not source.is_file():
                    continue

                if asset.kind == "launch-image":
                    if options.launch_image != asset.name: continue
                    version = str(entry.get("minimum-system-version", "7.0"))
                    version_tag = "".join(ch for ch in version if ch.isdigit()).ljust(3, "0")
                    scale_suffix = "" if scale_text == "1x" else f"@{scale_text}"
                    idiom_suffix = "~ipad" if idiom == "ipad" else ""
                    launch_path = options.output / f"{asset.name}-{version_tag}{scale_suffix}{idiom_suffix}.png"
                    if launch_path not in outputs:
                        launch_path.write_bytes(source.read_bytes()); outputs.append(launch_path)
                    occupied_slots.add(slot); continue

                try:
                    if asset.kind == "data":
                        renditions.append(data_rendition(asset.name, source.read_bytes(),
                                                         str(entry.get("universal-type-identifier", "public.data")),
                                                         idiom=idiom, appearance=appearance, localization=localization))
                    elif asset.kind == "image" and source.suffix.lower() in (".jpg", ".jpeg"):
                        renditions.append(jpeg_rendition(asset.name, source.read_bytes(), filename, scale=scale_value,
                                                         idiom=idiom, appearance=appearance, localization=localization))
                    elif asset.kind == "image" and source.suffix.lower() in (".heif", ".heic"):
                        renditions.append(heif_rendition(asset.name, source.read_bytes(), filename, scale=scale_value,
                                                         idiom=idiom, appearance=appearance, localization=localization))
                    elif asset.kind == "image" and source.suffix.lower() == ".png":
                        renditions.append(png_rendition(asset.name, source.read_bytes(), filename, scale=scale_value,
                                                        idiom=idiom, appearance=appearance, localization=localization))
                    elif asset.kind == "symbol" and source.suffix.lower() == ".svg":
                        renditions.append(symbol_rendition(asset.name, source.read_bytes(), filename))
                    elif asset.kind == "image" and source.suffix.lower() == ".svg":
                        renditions.extend(svg_renditions(asset.name, source.read_bytes(), filename))
                    else:
                        continue
                    occupied_slots.add(slot)
                except ValueError as exc:
                    diagnostics.append(Diagnostic("error", f"asset encoder limitation: {exc}", asset.directory))

        if options.app_icon and any(asset.kind == "app-icon" and asset.name == options.app_icon and asset.entries
                                    for asset in assets) and options.app_icon not in app_icon_emitted:
            diagnostics.append(Diagnostic("error", f'The stickers icon set, app icon set, or icon stack named "{options.app_icon}" did not have any applicable content.'))

        if renditions and not any(item.severity == "error" for item in diagnostics):
            thinning_arguments = ""
            if len(options.target_devices) == 1:
                from .thinning import ThinningOptions, thin_renditions
                device_idioms = {"iphone":"iphone","ipad":"ipad","tv":"tv","watch":"watch","mac":"mac","vision":"vision"}
                thinning = ThinningOptions(idiom=device_idioms[options.target_devices[0]])
                renditions = thin_renditions(renditions, thinning)
                thinning_arguments = thinning.metadata_arguments()
            if options.filter_for_device_model: thinning_arguments += (" " if thinning_arguments else "") + "model " + options.filter_for_device_model
            if options.filter_for_device_os_version: thinning_arguments += (" " if thinning_arguments else "") + "os-version " + options.filter_for_device_os_version
            car_path = options.output / "Assets.car"
            car_path.write_bytes(build_assets_car(renditions, platform=options.platform or "macosx",
                                                   target=options.minimum_deployment_target or "13.0",
                                                   thinning_arguments=thinning_arguments))
            outputs.append(car_path)
    if deferred_partial_info is not None:
        if missing_app_icon and missing_launch_image:
            outputs.insert(0, deferred_partial_info)
        else:
            outputs.append(deferred_partial_info)
    if missing_app_icon:
        diagnostics.append(Diagnostic(
            "error",
            f'None of the input catalogs contained a matching stickers icon set, app icon set, or icon stack named  "{options.app_icon}".',
        ))
    if missing_launch_image:
        diagnostics.append(Diagnostic(
            "error",
            f'None of the input catalogs contained a matching launch image set named  "{options.launch_image}".',
        ))
    return CompileResult(catalogs, diagnostics, outputs)
