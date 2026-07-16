"""Apple-style actool result plist and human-readable text serialization."""
from __future__ import annotations
import plistlib
from pathlib import Path
from .model import Diagnostic

_KEYS = {"error": "com.apple.actool.errors", "warning": "com.apple.actool.warnings", "notice": "com.apple.actool.notices"}

ACTOOL_BUNDLE_VERSIONS = {
    "16.0": "23094", "16.1": "23504", "16.2": "23504", "16.3": "23727", "16.4": "23727",
    "26.0.1": "24128", "26.1.1": "24412", "26.2": "24506", "26.3": "24506",
    "26.4.1": "24765", "26.5": "24765", "26.6": "24765",
}

def version_plist(bundle_version: str | None = None, short_version: str = "26.5") -> bytes:
    if bundle_version is None:
        try:
            bundle_version = ACTOOL_BUNDLE_VERSIONS[short_version]
        except KeyError as exc:
            raise ValueError(f"unsupported Xcode compatibility version: {short_version}") from exc
    root = {"com.apple.actool.version": {"bundle-version": bundle_version, "short-bundle-version": short_version}}
    return plistlib.dumps(root, fmt=plistlib.FMT_XML, sort_keys=False)


def unknown_argument_plist(argument: str, *, include_missing_input: bool = False, only_missing_input: bool = False) -> bytes:
    rows = []
    if not only_missing_input and argument:
        rows.append({"description": f"Unknown argument '{argument}'."})
    if only_missing_input or include_missing_input:
        rows.append({"description": "Not enough arguments provided; where is the input document to operate on?"})
    root = {"com.apple.actool.errors": rows}
    return plistlib.dumps(root, fmt=plistlib.FMT_XML, sort_keys=False)


def result_plist(diagnostics: list[Diagnostic], outputs: list[Path], *, include_compilation_results: bool = False) -> bytes:
    root: dict[str, object] = {}
    if outputs or include_compilation_results:
        root["com.apple.actool.compilation-results"] = {"output-files": [str(x) for x in outputs]}
    document_errors = [d.document for d in diagnostics if d.document is not None]
    if document_errors:
        root["com.apple.actool.document.errors"] = document_errors
    for severity in ("error", "warning", "notice"):
        rows = []
        for d in diagnostics:
            if d.severity != severity:
                continue
            item = {"description": d.message}
            if d.failure_reason is not None:
                item["failure-reason"] = d.failure_reason
            if d.path is not None:
                item["source-path"] = str(d.path)
            rows.append(item)
        if rows:
            root[_KEYS[severity]] = rows
    return plistlib.dumps(root, fmt=plistlib.FMT_XML, sort_keys=False)


def render_human_readable(diagnostics: list[Diagnostic], outputs: list[Path], *, include_compilation_results: bool = False) -> str:
    lines: list[str] = []
    if outputs or include_compilation_results:
        lines.append("/* com.apple.actool.compilation-results */")
        for x in outputs:
            lines.append(str(x))
        if outputs:
            lines.append("")
    for severity, header in (("error", "/* com.apple.actool.errors */"), ("warning", "/* com.apple.actool.warnings */"), ("notice", "/* com.apple.actool.notices */")):
        matching = [d for d in diagnostics if d.severity == severity]
        if not matching:
            continue
        lines.append(header)
        for d in matching:
            prefix = f"{d.path}: {severity}: " if d.path else f"{severity}: "
            lines.append(f"{prefix}{d.message}")
            if d.failure_reason is not None:
                lines.append(f"    Failure Reason: {d.failure_reason}")
    return "\n".join(lines)
