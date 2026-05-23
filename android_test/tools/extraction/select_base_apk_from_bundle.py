#!/usr/bin/env python3
"""Canonical pre-acquire utility: select the base APK from an .xapk/.apkm/.apks bundle.

**Rule** (CP34 Gate I-6 ratified 2026-05-23, MAC-239 Wave G/H v1 integration):
The base APK is identified by the bundle's manifest file, NOT by file size.

For .xapk bundles: parse `manifest.json`, find entry in `split_apks` where
  `id == "base"`; extract that APK.
For .apkm bundles: parse `info.json`, locate the base APK entry similarly.
For .apks bundles (Bundletool format): the `base/` directory holds base.apk.

The naive "largest .apk in bundle" heuristic produces SILENT FAILURES on Android
App Bundle splits where `config.<arch>.apk` (native libs split) is larger than
`base.apk`. Track A bit this twice in the Wave G/H v1 CCTV cohort (Hanwha,
Uniview); pipeline ran against a zero-classes APK and surfaced no candidates
until re-extraction with the manifest-based rule.

Usage:
    python3 select_base_apk_from_bundle.py <bundle.xapk|.apkm|.apks> [--out-dir DIR]

Exit 0 + writes selected base apk to <out-dir>/base.apk on success.
Exit 1 if manifest missing or no base entry found (halt — never fall back to
largest-apk heuristic).
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path


def select_xapk_base(bundle_zip: zipfile.ZipFile, bundle_path: Path) -> str:
    """Return the filename inside the xapk that should be extracted as base.apk.

    .xapk manifest schema: {"split_apks": [{"id": "base", "file": "...base.apk"}, ...]}
    """
    with bundle_zip.open('manifest.json') as f:
        manifest = json.load(f)
    splits = manifest.get('split_apks') or []
    for entry in splits:
        if entry.get('id') == 'base':
            return entry['file']
    raise RuntimeError(
        f'xapk manifest at {bundle_path} has no split_apks entry with id="base". '
        f'Got ids: {[e.get("id") for e in splits]}. '
        f'HALT — do not fall back to largest-apk heuristic.'
    )


def select_apkm_base(bundle_zip: zipfile.ZipFile, bundle_path: Path) -> str:
    """Return the filename inside the apkm that should be extracted as base.apk.

    .apkm info.json schema (APKMirror): top-level `apk_title` + nested `splits` array
    where one entry has `id == "base"` or `name == "base.apk"`.
    """
    with bundle_zip.open('info.json') as f:
        info = json.load(f)
    splits = info.get('splits') or info.get('split_apks') or []
    for entry in splits:
        if entry.get('id') == 'base' or entry.get('name') == 'base.apk':
            return entry.get('file') or entry.get('name')
    # APKMirror sometimes stores base.apk directly at the bundle root
    namelist = bundle_zip.namelist()
    if 'base.apk' in namelist:
        return 'base.apk'
    raise RuntimeError(
        f'apkm info.json at {bundle_path} has no base entry; namelist has no base.apk. '
        f'HALT — do not fall back to largest-apk heuristic.'
    )


def select_apks_base(bundle_zip: zipfile.ZipFile, bundle_path: Path) -> str:
    """Return the filename inside the .apks (Bundletool) bundle for base APK.

    Bundletool .apks layout: `splits/base-master.apk` or `base/` directory.
    """
    candidates = ['splits/base-master.apk', 'base-master.apk', 'base/base.apk', 'base.apk']
    namelist = bundle_zip.namelist()
    for c in candidates:
        if c in namelist:
            return c
    raise RuntimeError(
        f'apks bundle at {bundle_path} has no base-master.apk candidate. '
        f'Tried {candidates}. HALT — do not fall back to largest-apk heuristic.'
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', help='path to .xapk/.apkm/.apks bundle')
    p.add_argument('--out-dir', default='.', help='where to write extracted base.apk')
    args = p.parse_args()

    bundle = Path(args.bundle).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = bundle.suffix.lower()
    if suffix not in ('.xapk', '.apkm', '.apks'):
        print(f'Unsupported bundle suffix: {suffix}', file=sys.stderr)
        return 2

    with zipfile.ZipFile(bundle) as zf:
        if suffix == '.xapk':
            base_member = select_xapk_base(zf, bundle)
        elif suffix == '.apkm':
            base_member = select_apkm_base(zf, bundle)
        else:
            base_member = select_apks_base(zf, bundle)

        target = out_dir / 'base.apk'
        with zf.open(base_member) as src, open(target, 'wb') as dst:
            dst.write(src.read())

    print(f'OK selected manifest-base member: {base_member}')
    print(f'OK wrote: {target}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
