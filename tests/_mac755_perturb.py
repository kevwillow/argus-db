"""MAC-755 negative-control plugin — perturb the extractor's OUTPUT.

A cohort test that passes after being repointed at a frozen snapshot proves
nothing until it has been shown it can still go red.  This plugin wraps each
cohort extractor's build function and corrupts its return value, so the driver
(``scripts/mac755_negative_control.py``) can prove each repointed file still
fails when the extractor lies.

It is NEVER loaded by a normal ``pytest tests/`` run — it activates only when
explicitly requested with ``-p _mac755_perturb`` and ``MAC755_PERTURB=<mode>``.

Modes
-----
``drop``     Remove one promoted candidate.  Catches the re-baselining failure
             mode the issue calls out: if anyone had "fixed" the tests by
             editing an expected count down to 0 or a set to ``set()``, the file
             would stay GREEN here.
``verdict``  Flip a candidate's DB-presence verdict from net-new to held.
             Catches the loud ``net_new`` assertion going vacuous.
``cite``     Corrupt an identifier / byte-form.  Catches cite-faithfulness and
             byte-form assertions going vacuous.

Patching happens in ``pytest_configure``, which runs before collection — the
cohort test modules call ``build()`` at import time, so a later hook is too late.
"""
from __future__ import annotations

import copy
import os

MODES = ("drop", "verdict", "cite")


def _corrupt_str(s):
    """Flip the first hex-ish character so the value is no longer byte-faithful."""
    if not isinstance(s, str) or not s:
        return s
    for i, ch in enumerate(s):
        if ch in "0123456789abcdefABCDEF":
            repl = "9" if ch.lower() != "9" else "0"
            return s[:i] + repl + s[i + 1:]
    return s + "X"


# --- per-cohort perturbations ------------------------------------------------
# Each takes the build() return value and the mode, and returns a corrupted copy.

def _p_cohort1(out, mode):
    cands, behavioral = out
    cands = copy.deepcopy(cands)
    if mode == "drop":
        cands.pop(0)
    elif mode == "verdict":
        # the AirTag 128-bit UUID is the one the module says is net-new
        for c in cands:
            if c.get("already_in_db") is False:
                c["already_in_db"] = True
                break
    elif mode == "cite":
        cands[0]["value"] = _corrupt_str(cands[0]["value"])
    return cands, behavioral


def _p_db_presence(out, mode, list_key="candidates"):
    """Shared shape: {'candidates': [{'value','db_presence',...}], '_meta': ...}."""
    out = copy.deepcopy(out)
    cands = out[list_key]
    if mode == "drop":
        cands.pop(0)
    elif mode == "verdict":
        flipped = False
        for c in cands:
            if c.get("db_presence") == "net-new":
                c["db_presence"] = "already_in_db:id=999999"
                flipped = True
                break
        if not flipped:  # cohorts with 0 net-new: flip the other way
            for c in cands:
                if str(c.get("db_presence", "")).startswith("already_in_db"):
                    c["db_presence"] = "net-new"
                    break
    elif mode == "cite":
        cands[0]["value"] = _corrupt_str(cands[0].get("value"))
    return out


def _p_cohort2(out, mode):
    return _p_db_presence(out, mode)


def _p_cohort3_drones(out, mode):
    return _p_db_presence(out, mode)


def _p_cohort3_bletracker(out, mode):
    return _p_db_presence(out, mode)


def _p_cohort4(out, mode):
    out = copy.deepcopy(out)
    if mode == "drop":
        out["gatt_candidates"].pop(0)
    elif mode == "verdict":
        # c4 records the verdict in notes; the counts carry the promoted total
        out["gatt_candidates"][0]["notes"]["net_new_vs_held"] = "already_in_db:id=999999"
        out["counts"]["gatt_clean_promote"] -= 1
    elif mode == "cite":
        c = out["gatt_candidates"][0]
        c["raw_payload"]["byte_form"] = _corrupt_str(c["raw_payload"]["byte_form"])
    return out


def _p_cohort5(out, mode):
    out = copy.deepcopy(out)
    if mode == "drop":
        out["net_new_oui_total"] -= 1
    elif mode == "verdict":
        for brand in out["tally"]["pure_play"].values():
            if brand.get("net_new_oui"):
                brand["net_new_oui"] -= 1
                break
    elif mode == "cite":
        # direct indexing on purpose: a shape change must raise, not silently
        # no-op into a fake "gate is a hole" verdict
        out["sig_company_id_reference"][0]["db_presence"] = "ABSENT(unexpected)"
    return out


def _p_cohort6(out, mode):
    out = copy.deepcopy(out)
    if mode == "drop":
        out["candidates"].pop(0)
        out["counts"]["ble_service_uuid_promote"] -= 1
    elif mode == "verdict":
        out["candidates"][0]["net_new"] = False
    elif mode == "cite":
        c = out["candidates"][0]
        c["source_markers"]["byte_form"] = _corrupt_str(c["source_markers"]["byte_form"])
    return out


PERTURBATIONS = {
    ("db.sources.cohort1_ble_trackers", "build"): _p_cohort1,
    ("db.sources.cohort2_alpr_copcar", "build"): _p_cohort2,
    ("db.sources.cohort3_bletracker", "build"): _p_cohort3_bletracker,
    ("db.sources.cohort3_drones", "build"): _p_cohort3_drones,
    ("db.sources.cohort4_smartlock", "build"): _p_cohort4,
    ("db.sources.cohort5_consumer", "build_candidates"): _p_cohort5,
    ("db.sources.cohort6_petkid", "build"): _p_cohort6,
}


def pytest_configure(config):
    mode = os.environ.get("MAC755_PERTURB")
    if not mode:
        return
    if mode not in MODES:
        raise SystemExit(f"MAC755_PERTURB must be one of {MODES}, got {mode!r}")
    import importlib

    for (modname, fnname), perturb in PERTURBATIONS.items():
        mod = importlib.import_module(modname)
        original = getattr(mod, fnname)

        def make(original=original, perturb=perturb, label=f"{modname}.{fnname}"):
            def wrapper(*a, **kw):
                clean = original(*a, **kw)
                dirty = perturb(copy.deepcopy(clean), mode)
                # A perturbation that changed nothing would let a live gate be
                # reported as a hole. Fail loudly instead.
                if dirty == clean:
                    raise AssertionError(
                        f"MAC-755 negative control is broken: mode={mode} was a "
                        f"no-op on {label}. Fix the perturbation before reading "
                        "any verdict from this run.")
                return dirty
            return wrapper

        setattr(mod, fnname, make())
    config.stash  # touch, keeps linters quiet about the unused arg
    print(f"\n[MAC-755 negative control] extractor output perturbed: mode={mode}")
