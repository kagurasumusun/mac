from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import plistlib

from .carwriter import (
    AssetRendition, app_icon_renditions, build_assets_car, color_rendition, data_rendition,
    heif_rendition, jpeg_rendition, layered_image_renditions, make_deepmap_csi_variant, png_rendition, resize_png, svg_renditions, symbol_rendition, png_dimensions,
    _identifier,
)
from .atlas import packed_atlas_renditions, packed_watch_complication_renditions
from .imagestack import StackLayerImage, imagestack_renditions
from .model import Asset, Catalog, Diagnostic, load_catalog
from .appicons import app_icon_entry_rank, app_icon_sidecar_specs


def _resolve_image_stack_layers(asset: Asset, assets: list[Asset]) -> list[dict[str, object]]:
    """Resolve an image stack's layer references to concrete image entries.

    Returns front-to-back order as declared in the stack's Contents.json.
    Each row carries layer_name, filename, base directory, idiom, scale.
    """
    layers: list[dict[str, object]] = []
    for layer_ref in asset.entries:
        dirname = layer_ref.get("filename")
        if not isinstance(dirname, str):
            continue
        layer_dir = asset.directory / dirname
        layer_asset = next((c for c in assets if c.kind == "image-stack-layer" and c.directory == layer_dir), None)
        if layer_asset is None:
            continue
        nested_image = next((c for c in assets if c.kind == "image" and c.directory.parent == layer_dir), None)
        if nested_image is not None:
            candidates = list(nested_image.entries)
            selected_base = nested_image.directory
        else:
            candidates = list(layer_asset.entries)
            selected_base = layer_dir
        entry = next((e for e in candidates if isinstance(e.get("filename"), str) and (selected_base / str(e["filename"])).is_file()), None)
        if entry is None:
            continue
        layers.append({
            "layer_name": layer_asset.name,
            "filename": str(entry["filename"]),
            "base": selected_base,
            "idiom": str(entry.get("idiom", "universal")),
            "scale": str(entry.get("scale", "1x")),
        })
    return layers


def compile_brand_assets(asset: Asset, assets: list[Asset], options: CompileOptions) -> tuple[list[AssetRendition], list[Diagnostic]]:
    """Compile a tvOS .brandassets directory (roles: app icon stacks + shelves).

    Observed materialization gate (Xcode 26.x): only when
    `--target-device tv` and `--app-icon <brand name>` are both passed does
    Apple actool emit a CAR for public .brandassets content.
    """
    renditions: list[AssetRendition] = []
    diagnostics: list[Diagnostic] = []
    if "tv" not in options.target_devices or options.app_icon != asset.name:
        return renditions, diagnostics
    stacks: list[tuple[dict[str, object], Asset]] = []
    shelves: list[tuple[dict[str, object], Asset]] = []
    for entry in asset.entries:
        filename = entry.get("filename")
        role = str(entry.get("role", ""))
        if not isinstance(filename, str):
            continue
        target = asset.directory / filename
        if role == "primary-app-icon" and target.suffix == ".imagestack":
            stack_asset = next((c for c in assets if c.kind == "image-stack" and c.directory == target), None)
            if stack_asset is not None:
                stacks.append((entry, stack_asset))
        elif role in ("top-shelf-image", "top-shelf-image-wide") and target.suffix == ".imageset":
            image_asset = next((c for c in assets if c.kind == "image" and c.directory == target), None)
            if image_asset is not None:
                shelves.append((entry, image_asset))
    if not stacks:
        return renditions, diagnostics
    # The primary (non-marketing) stack provides the aggregate identifier used
    # by all aggregate records of both stacks (observed Apple behavior).
    primary_name = next((s.name for _e, s in stacks if str(_e.get("size", "")) != "1280x768"), stacks[0][1].name)
    primary_id = _identifier(primary_name)
    for entry, stack_asset in stacks:
        resolved = _resolve_image_stack_layers(stack_asset, assets)
        if len(resolved) < 2:
            continue
        layers = [StackLayerImage(str(layer["layer_name"]), str(layer["filename"]), (layer["base"] / str(layer["filename"])).read_bytes())
                  for layer in reversed(resolved)]
        marketing = str(entry.get("size", "")) == "1280x768"
        scale = int(str(resolved[0].get("scale", "1x"))[0]) if str(resolved[0].get("scale", "1x"))[0] in "123" else 1
        if marketing:
            renditions.extend(imagestack_renditions(stack_asset.name, layers, root_idiom=6, child_idiom=6, flattened_idiom=6, scale=scale, root_identifier=primary_id))
        else:
            renditions.extend(imagestack_renditions(stack_asset.name, layers, root_idiom=0, child_idiom=3, flattened_idiom=3, scale=scale, root_identifier=primary_id))
    for _entry, image_asset in shelves:
        chosen = next((e for e in image_asset.entries
                       if isinstance(e.get("filename"), str) and str(e.get("idiom", "tv")) == "tv"
                       and (image_asset.directory / str(e["filename"])).is_file()), None)
        if chosen is None:
            chosen = next((e for e in image_asset.entries
                           if isinstance(e.get("filename"), str) and (image_asset.directory / str(e["filename"])).is_file()), None)
        if chosen is None:
            continue
        png = (image_asset.directory / str(chosen["filename"])).read_bytes()
        scale_text = str(chosen.get("scale", "1x"))
        scale = int(scale_text[0]) if scale_text and scale_text[0] in "123" else 1
        try:
            csi = make_deepmap_csi_variant(png, str(chosen["filename"]), scale=scale, prefer_cbck=True, stack_bottom=True)
        except ValueError as exc:
            diagnostics.append(Diagnostic("error", f"invalid top shelf image: {exc}", image_asset.directory))
            continue
        renditions.append(AssetRendition(image_asset.name, csi, 181, 181, scale=scale, idiom=3))
    return renditions, diagnostics


@dataclass
class CompileOptions:
    output: Path
    platform: str | None = None
    minimum_deployment_target: str | None = None
    app_icon: str | None = None
    accent_color: str | None = None
    launch_image: str | None = None
    complication: str | None = None
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
    platform = (options.platform or "").lower()
    if options.app_icon and options.app_icon in names and platform in ("iphoneos", "iphonesimulator", "ios"):
        primary = {
            "CFBundleIconFiles": ["AppIcon60x60"],
            "CFBundleIconName": options.app_icon,
        }
        result["CFBundleIcons"] = {"CFBundlePrimaryIcon": primary}
        result["CFBundleIcons~ipad"] = {
            "CFBundlePrimaryIcon": {
                "CFBundleIconFiles": ["AppIcon60x60", "AppIcon76x76"],
                "CFBundleIconName": options.app_icon,
            }
        }
    if options.app_icon and "tv" in options.target_devices and platform in ("appletvos", "appletvsimulator"):
        for catalog in catalogs:
            for asset in catalog.assets:
                if asset.kind != "brand-assets" or asset.name != options.app_icon:
                    continue
                primary = shelf = shelf_wide = None
                for entry in asset.entries:
                    role = str(entry.get("role", ""))
                    fn = entry.get("filename")
                    if not isinstance(fn, str) or "." not in fn:
                        continue
                    stem = fn.rsplit(".", 1)[0]
                    if role == "primary-app-icon" and str(entry.get("size", "")) != "1280x768":
                        primary = stem
                    elif role == "top-shelf-image":
                        shelf = stem
                    elif role == "top-shelf-image-wide":
                        shelf_wide = stem
                if primary is not None:
                    result["CFBundleIcons"] = {"CFBundlePrimaryIcon": primary}
                tv: dict[str, str] = {}
                if shelf is not None:
                    tv["TVTopShelfPrimaryImage"] = shelf
                if shelf_wide is not None:
                    tv["TVTopShelfPrimaryImageWide"] = shelf_wide
                if tv:
                    result["TVTopShelfImage"] = tv
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
                # Observed Xcode 26.x writes the partial-info plist as XML.
                plistlib.dump(_partial_info(catalogs, options), stream, fmt=plistlib.FMT_XML)
            # actool lists primary compiled products before this auxiliary plist.
            deferred_partial_info = options.partial_info_plist

        assets = [asset for catalog in catalogs for asset in catalog.assets]
        renditions = []
        occupied_slots: set[tuple[object, ...]] = set()
        app_icon_emitted: set[str] = set()
        app_icon_had_applicable_slot: set[str] = set()
        known_idioms = {"universal","iphone","ipad","tv","watch","mac","vision","car","marketing"}

        def color_component(components: dict[str, object], name: str, default: float = 0.0) -> float:
            value = components.get(name)
            if value is None: return default
            if isinstance(value, int): return value / 255.0
            if isinstance(value, float): return value
            text = str(value).strip()
            if not text: return default
            if "." not in text and "e" not in text.lower():
                try: return int(text, 0) / 255.0
                except ValueError: pass
            return float(text)

        def layer_depth(entry: dict[str, object], fallback: int) -> int:
            value = entry.get("depth")
            if value is None:
                value = entry.get("dimension2")
            if value is None:
                return fallback
            if isinstance(value, int):
                depth = value
            else:
                text = str(value).strip()
                if not text:
                    return fallback
                depth = int(text, 0)
            if not 0 <= depth <= 65535:
                raise ValueError("layer depth must be between 0 and 65535")
            return depth

        distill_failed = False

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

        atlas_member_dirs = {asset.directory for asset in assets if asset.directory.parent.suffix == ".spriteatlas"}

        for asset in assets:
            if asset.kind == "sprite-atlas":
                members = [candidate for candidate in assets if candidate.kind == "image" and candidate.directory.parent == asset.directory]
                images: dict[str, bytes] = {}
                for member in members:
                    selected = next((entry for entry in member.entries if isinstance(entry.get("filename"), str) and (member.directory / str(entry["filename"])).is_file() and str(entry.get("scale", "1x")) == "1x"), None)
                    if selected is None:
                        selected = next((entry for entry in member.entries if isinstance(entry.get("filename"), str) and (member.directory / str(entry["filename"])).is_file()), None)
                    if selected is None:
                        continue
                    source = member.directory / str(selected["filename"])
                    if source.suffix.lower() != ".png":
                        continue
                    images[member.name] = source.read_bytes()
                if images:
                    try:
                        renditions.extend(packed_atlas_renditions(
                            images,
                            scale=1,
                            style="explicit",
                            atlas_name=asset.name,
                        ))
                    except ValueError as exc:
                        diagnostics.append(Diagnostic("error", f"invalid sprite atlas: {exc}", asset.directory))
                continue
            if asset.kind == "complication-set":
                if options.complication and options.complication != asset.name:
                    continue
                complication_images: list[tuple[str, bytes]] = []
                for ref in asset.entries:
                    dirname = ref.get("filename")
                    role = str(ref.get("role", ""))
                    if not isinstance(dirname, str) or not role:
                        continue
                    image_asset = next((candidate for candidate in assets if candidate.kind == "image" and candidate.directory == asset.directory / dirname), None)
                    if image_asset is None:
                        continue
                    selected = next((entry for entry in image_asset.entries if isinstance(entry.get("filename"), str) and (image_asset.directory / str(entry["filename"])).is_file() and str(entry.get("scale", "1x")) == "2x"), None)
                    if selected is None:
                        selected = next((entry for entry in image_asset.entries if isinstance(entry.get("filename"), str) and (image_asset.directory / str(entry["filename"])).is_file()), None)
                    if selected is None:
                        continue
                    source = image_asset.directory / str(selected["filename"])
                    if source.suffix.lower() != ".png":
                        continue
                    complication_images.append((f"{asset.name}/{role.capitalize()}", source.read_bytes()))
                if complication_images:
                    try:
                        renditions.extend(packed_watch_complication_renditions(complication_images, scale=2, atlas_name=asset.name))
                    except ValueError as exc:
                        diagnostics.append(Diagnostic("error", f"invalid complication set: {exc}", asset.directory))
                continue
            if asset.kind == "image-stack" and asset.directory.parent.suffix != ".brandassets":
                platform = (options.platform or "appletvos").lower()
                is_vision_stack = platform in ("xros", "xrsimulator", "visionos")
                if is_vision_stack:
                    pass  # handled by the legacy vision branch below
                else:
                    resolved_layers = _resolve_image_stack_layers(asset, assets)
                    applicable = [layer for layer in resolved_layers if layer["idiom"] in ("universal",)]
                    if len(resolved_layers) >= 2 and len(applicable) < 2:
                        if not applicable:
                            detail = "none have applicable content"
                        elif len(applicable) == 1:
                            detail = "only 1 has applicable content"
                        else:
                            detail = f"only {len(applicable)} have applicable content"
                        message = (f'The image stack "{asset.name}" must have at least 2 layers with applicable content. '
                                   f"Although it has {len(resolved_layers)} layers, {detail}.")
                        diagnostics.append(Diagnostic("document", message, asset.directory,
                                                      document={"affected-items": [f"./{asset.directory.name}"],
                                                                "catalog": str(asset.catalog),
                                                                "message": message,
                                                                "type": "Unsupported Configuration"}))
                        continue
                    if len(applicable) >= 2:
                        try:
                            renditions.extend(imagestack_renditions(
                                asset.name,
                                [StackLayerImage(layer["layer_name"], layer["filename"], (layer["base"] / layer["filename"]).read_bytes())
                                 for layer in reversed(applicable)],
                                root_idiom=0, child_idiom=0, flattened_idiom=0,
                                scale=int(str(applicable[0].get("scale", "1x"))[0]) if str(applicable[0].get("scale", "1x"))[0] in "123" else 1))
                        except ValueError as exc:
                            diagnostics.append(Diagnostic("error", f"invalid image stack: {exc}", asset.directory))
                    continue
            if asset.kind == "image-stack" and asset.directory.parent.suffix == ".brandassets":
                continue
            if asset.kind == "image-stack":
                layer_bytes: list[bytes] = []
                layer_depths: list[int] = []
                stack_scale = 1
                platform = (options.platform or "appletvos").lower()
                is_vision_stack = platform in ("xros", "xrsimulator", "visionos")
                invalid_stack = False
                for layer_ref in asset.entries:
                    dirname = layer_ref.get("filename")
                    if not isinstance(dirname, str):
                        continue
                    layer_dir = asset.directory / dirname
                    layer_asset = next((candidate for candidate in assets if candidate.kind == "image-stack-layer" and candidate.directory == layer_dir), None)
                    if layer_asset is None:
                        continue
                    selected = next((entry for entry in layer_asset.entries if isinstance(entry.get("filename"), str) and (layer_dir / str(entry["filename"])).is_file()), None)
                    selected_base = layer_dir
                    selected_props: dict[str, object] = dict(layer_asset.properties)
                    if selected is None:
                        nested_image = next((candidate for candidate in assets if candidate.kind == "image" and candidate.directory.parent == layer_dir), None)
                        if nested_image is None:
                            continue
                        selected = next((entry for entry in nested_image.entries if isinstance(entry.get("filename"), str) and (nested_image.directory / str(entry["filename"])).is_file()), None)
                        if selected is None:
                            continue
                        selected_base = nested_image.directory
                        selected_props.update(nested_image.properties)
                    scale_text = str(selected.get("scale", "1x"))
                    if scale_text in ("1x", "2x", "3x"):
                        stack_scale = int(scale_text[0])
                    layer_bytes.append((selected_base / str(selected["filename"])).read_bytes())
                    if is_vision_stack:
                        try:
                            depth_source = dict(selected_props)
                            depth_source.update(selected)
                            depth_source.update(layer_ref)
                            layer_depths.append(layer_depth(depth_source, len(layer_depths) + 1))
                        except ValueError as exc:
                            diagnostics.append(Diagnostic("error", f"invalid image stack: {exc}", asset.directory))
                            invalid_stack = True
                            break
                if layer_bytes and not invalid_stack:
                    idiom = "vision" if is_vision_stack else "tv"
                    try:
                        renditions.extend(layered_image_renditions(
                            asset.name, layer_bytes, idiom=idiom, scale=stack_scale,
                            depths=layer_depths or None,
                        ))
                    except ValueError as exc:
                        diagnostics.append(Diagnostic("error", f"invalid image stack: {exc}", asset.directory))
                continue
            if asset.kind == "image-stack-layer":
                continue
            if asset.kind == "brand-assets":
                brand_out, brand_diags = compile_brand_assets(asset, assets, options)
                renditions.extend(brand_out)
                diagnostics.extend(brand_diags)
                continue

            # Real AppIcon catalogs commonly contain many legacy sizes.  Select
            # the largest dimension-applicable source (normally the modern
            # 1024x1024 marketing slot) instead of whichever entry appears first.
            if asset.kind == "app-icon":
                if options.app_icon != asset.name:
                    continue
                candidates: list[tuple[int, int, int, int, bytes, str]] = []
                for icon_entry in asset.entries:
                    filename = icon_entry.get("filename")
                    if not isinstance(filename, str):
                        continue
                    source = asset.directory / filename
                    if not source.is_file():
                        continue
                    try:
                        rank = app_icon_entry_rank(icon_entry, options.platform or "iphoneos")
                    except ValueError as exc:
                        diagnostics.append(Diagnostic("error", f"invalid AppIcon: {exc}", asset.directory))
                        break
                    if rank is None:
                        continue
                    app_icon_had_applicable_slot.add(asset.name)
                    try:
                        source_png = source.read_bytes(); actual = png_dimensions(source_png)
                        declared = str(icon_entry.get("size", "")); scale_text = str(icon_entry.get("scale", "1x"))
                        if declared:
                            points = declared.split("x", 1); scale = int(scale_text[:-1]) if scale_text.endswith("x") else 1
                            expected = (round(float(points[0]) * scale), round(float(points[1]) * scale))
                            if actual != expected:
                                continue
                        candidates.append((rank, actual[0] * actual[1], actual[0], actual[1], source_png, filename))
                    except ValueError:
                        # Syntactically invalid AppIcon size/source slots are
                        # silently ignored; the partial plist is still emitted.
                        app_icon_emitted.add(asset.name)
                        continue
                if candidates:
                    _, _, _, _, source_png, filename = max(candidates, key=lambda row: row[:4] + (row[5],))
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
                if asset.directory in atlas_member_dirs:
                    continue
                if asset.directory.parent.suffix in (".imagestacklayer", ".solidimagestacklayer", ".complicationset"):
                    continue
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
                        if not isinstance(components, dict): raise ValueError("color components must be a dictionary")
                        values = [color_component(components, name, 0.0) for name in ("red", "green", "blue")]
                        values.append(color_component(components, "alpha", 1.0))
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
                    if asset.kind == "image" and source.suffix.lower() == ".png":
                        distill_failed = True
                        diagnostics.append(Diagnostic("error", "Distill failed for unknown reasons."))
                    else:
                        diagnostics.append(Diagnostic("error", f"asset encoder limitation: {exc}", asset.directory))

        if options.app_icon and options.app_icon in app_icon_had_applicable_slot and options.app_icon not in app_icon_emitted:
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
        if distill_failed:
            # Apple leaves a structurally incomplete CAR on this failure path.
            # Emit a safe readable failure CAR while preserving its observable
            # output-file contract and nonzero exit status.
            car_path = options.output / "Assets.car"
            car_path.write_bytes(build_assets_car([data_rendition("__actool_distill_failure__", b"", "public.data")], platform=options.platform or "macosx", target=options.minimum_deployment_target or "13.0"))
            if car_path not in outputs: outputs.append(car_path)
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
