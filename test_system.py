#!/usr/bin/env python3
"""BRIDGE AI OS -- Full System Test (CI + DEV ready)"""
import os, sys, time, json, tempfile, traceback
from datetime import datetime

# --- UTF-8 force (critical for Windows) ---
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure 'app' package is importable (as it would be when uvicorn runs from backend/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# --- ANSI Colors ---
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def color(text, c):
    return f"{c}{text}{C.RESET}"

# --- Runner State ---
results = []
suite_stack = []
start_time = time.time()

CI_MODE = "--ci" in sys.argv
JSON_MODE = "--json" in sys.argv
QUIET = "--quiet" in sys.argv

def suite(name):
    suite_stack.append(name)
    if not QUIET and not JSON_MODE:
        print(f"\n{C.BOLD}{color(name, C.CYAN)}{C.RESET}")

def end_suite():
    if suite_stack:
        suite_stack.pop()

def test(name, fn):
    t0 = time.time()
    current_suite = suite_stack[-1] if suite_stack else "global"
    try:
        fn()
        duration = round((time.time() - t0) * 1000, 2)
        results.append({"suite": current_suite, "name": name, "status": "PASS", "duration_ms": duration})
        if not QUIET and not JSON_MODE:
            print(color(f"  [PASS] {name} ({duration}ms)", C.GREEN))
    except Exception as e:
        duration = round((time.time() - t0) * 1000, 2)
        results.append({"suite": current_suite, "name": name, "status": "FAIL", "error": str(e), "trace": traceback.format_exc(), "duration_ms": duration})
        if not QUIET and not JSON_MODE:
            print(color(f"  [FAIL] {name}", C.RED))
            print(color(f"         {e}", C.YELLOW))
        if CI_MODE:
            finalize(exit_code=1)

def summarize():
    summary = {}
    total_pass = total_fail = 0
    for r in results:
        s = r["suite"]
        summary.setdefault(s, {"pass": 0, "fail": 0})
        if r["status"] == "PASS":
            summary[s]["pass"] += 1; total_pass += 1
        else:
            summary[s]["fail"] += 1; total_fail += 1
    return summary, total_pass, total_fail

def finalize(exit_code=None):
    summary, total_pass, total_fail = summarize()
    duration = round(time.time() - start_time, 2)
    if JSON_MODE:
        print(json.dumps({"summary": summary, "total_pass": total_pass, "total_fail": total_fail, "duration_s": duration, "results": results, "timestamp": datetime.utcnow().isoformat()}, indent=2))
    else:
        print("\n" + "=" * 60)
        print(color("  TEST SUMMARY", C.BOLD))
        print("=" * 60)
        for s, data in summary.items():
            status = "PASS" if data["fail"] == 0 else "FAIL"
            col = C.GREEN if status == "PASS" else C.RED
            print(f"  {s:<30} {data['pass']+data['fail']:<5} {color(status, col)}")
        print("-" * 60)
        print(color(f"  TOTAL PASS: {total_pass}", C.GREEN))
        print(color(f"  TOTAL FAIL: {total_fail}", C.RED if total_fail else C.GREEN))
        print(color(f"  DURATION:   {duration}s", C.CYAN))
        print("=" * 60)
        if total_fail == 0:
            print(color("  ALL TESTS PASSED", C.GREEN))
        print("=" * 60)
    sys.exit(exit_code if exit_code is not None else (1 if total_fail else 0))

def assert_eq(a, b, msg=""):
    if a != b: raise AssertionError(msg or f"{a!r} != {b!r}")

def assert_true(x, msg=""):
    if not x: raise AssertionError(msg or "Expected True")

def assert_false(x, msg=""):
    if x: raise AssertionError(msg or "Expected False")


# =============================================================================
# ENV SETUP
# =============================================================================

os.environ['BRIDGE_SIWE_JWT_SECRET'] = 'a1b2c3d4e5f6' * 11
os.environ['BRIDGE_INTERNAL_SECRET'] = 'internal_secret_' * 4
os.environ['BRIDGE_ORCHESTRATOR_SECRET'] = 'orch_secret_key_' * 4
os.environ['NODE_ENV'] = 'development'
os.environ['JWT_SECRET'] = 'jwt_test_secret_' * 4

print("=" * 60)
print(color("  BRIDGE AI OS -- FULL SYSTEM TEST", C.BOLD))
print("=" * 60)

from backend.app.services.keyforge import (
    KeyForge, derive_key, current_epoch, epoch_range,
    _derive_master_secret, _rolling_entropy, KeyForgeToken,
    KEY_VERSION, EPOCH_DURATION_SEC
)

# =============================================================================
# 1. KEYFORGE CORE
# =============================================================================
suite("KeyForge Core")

def t_master():
    m = _derive_master_secret()
    assert_eq(len(m), 64)
    assert_eq(m, _derive_master_secret())
test("Master secret (64B, deterministic)", t_master)

def t_epoch():
    e = current_epoch()
    assert_true(e > 0)
    assert_eq(len(epoch_range(e)), 3)
test("Epoch computation + range", t_epoch)

def t_determinism():
    m = _derive_master_secret()
    e = current_epoch()
    assert_eq(derive_key(m, e, 'x'), derive_key(m, e, 'x'))
test("Key derivation determinism", t_determinism)

def t_scope_iso():
    m = _derive_master_secret()
    e = current_epoch()
    assert_true(derive_key(m, e, 'a') != derive_key(m, e, 'b'))
test("Scope isolation", t_scope_iso)

def t_keyid_iso():
    m = _derive_master_secret()
    e = current_epoch()
    assert_true(derive_key(m, e, 'x', key_id='1') != derive_key(m, e, 'x', key_id='2'))
test("Key ID isolation", t_keyid_iso)

def t_epoch_iso():
    m = _derive_master_secret()
    e = current_epoch()
    assert_true(derive_key(m, e, 'x') != derive_key(m, e+1, 'x'))
test("Epoch isolation", t_epoch_iso)

def t_entropy():
    m = _derive_master_secret()
    assert_eq(len(_rolling_entropy(m, current_epoch())), 32)
test("Rolling entropy (32 bytes)", t_entropy)

end_suite()

# =============================================================================
# 2. TOKEN LIFECYCLE
# =============================================================================
suite("Token Lifecycle")
forge = KeyForge.from_env()

def t_issue_validate():
    t = forge.issue('api-gateway')
    assert_true(t.startswith('kf2.'))
    r = forge.validate(t)
    assert_true(r.valid, f"Failed: {r.reason}")
    assert_eq(r.scope, 'api-gateway')
test("Issue + validate", t_issue_validate)

def t_all_scopes():
    for s in ['api-gateway','internal','orchestrator','economic','websocket','agent','webhook','admin']:
        assert_true(forge.validate(forge.issue(s)).valid, f"Scope {s} failed")
test("All 8 scopes", t_all_scopes)

def t_scope_mismatch():
    r = forge.validate(forge.issue('api-gateway'), required_scope='internal')
    assert_false(r.valid)
    assert_true('scope_mismatch' in r.reason)
test("Scope mismatch rejected", t_scope_mismatch)

def t_tampered_sig():
    t = forge.issue('internal')
    r = forge.validate(t[:-6] + 'abcdef')
    assert_false(r.valid)
    assert_eq(r.reason, 'invalid_signature')
test("Tampered signature rejected", t_tampered_sig)

def t_malformed():
    for bad in ['', 'garbage', 'kf2.', 'kf2.bad.data', 'kf1.old', 'Bearer xyz']:
        assert_false(forge.validate(bad).valid)
test("Malformed tokens rejected (6 variants)", t_malformed)

def t_roundtrip():
    t = forge.issue('webhook')
    p = KeyForgeToken.deserialize(t)
    assert_true(p is not None)
    assert_eq(p.scope, 'webhook')
    assert_true(forge.validate(p.serialize()).valid)
test("Token serialize/deserialize round-trip", t_roundtrip)

end_suite()

# =============================================================================
# 3. REVOCATION
# =============================================================================
suite("Revocation")
forge2 = KeyForge.from_env()

def t_key_revoke():
    forge2.add_key('tmp')
    t = forge2.issue('api-gateway', key_id='tmp')
    assert_true(forge2.validate(t).valid)
    forge2.remove_key('tmp')
    assert_false(forge2.validate(t).valid)
test("Key revocation", t_key_revoke)

def t_scope_revoke():
    t = forge2.issue('webhook')
    forge2.revoke_scope('webhook')
    assert_false(forge2.validate(t).valid)
    forge2.reinstate_scope('webhook')
    assert_true(forge2.validate(t).valid)
test("Scope revoke + reinstate", t_scope_revoke)

def t_revoke_blocks_issue():
    forge2.revoke_scope('admin')
    try:
        forge2.issue('admin')
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
    forge2.reinstate_scope('admin')
test("Cannot issue on revoked scope", t_revoke_blocks_issue)

end_suite()

# =============================================================================
# 4. CROSS-NODE SYNC
# =============================================================================
suite("Cross-Node Sync")

def t_cross_node():
    a, b = KeyForge.from_env(), KeyForge.from_env()
    assert_true(b.validate(a.issue('economic')).valid)
test("Token from node A validates on node B", t_cross_node)

def t_revoke_sync():
    a, b = KeyForge.from_env(), KeyForge.from_env()
    a.revoke_scope('agent')
    b.merge_remote_state(a.export_sync_state())
    t = KeyForge.from_env().issue('agent')
    assert_false(b.validate(t).valid)
test("Revocation propagates via sync", t_revoke_sync)

def t_key_removal_sync():
    a, b = KeyForge.from_env(), KeyForge.from_env()
    a.add_key('shared'); b.add_key('shared')
    a.remove_key('shared')
    b.merge_remote_state(a.export_sync_state())
    assert_true('shared' not in b.active_keys)
test("Key removal propagates (intersection)", t_key_removal_sync)

end_suite()

# =============================================================================
# 5. PERSISTENCE
# =============================================================================
suite("Persistence")

def t_persist():
    f = KeyForge.from_env()
    f.add_key('p-test'); f.revoke_scope('old')
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        path = tmp.name
    f.persist_state(path)
    f2 = KeyForge.from_env()
    assert_true(f2.restore_state(path))
    assert_true('p-test' in f2.active_keys)
    assert_true(f2.revocations.is_revoked('x', 'old'))
    os.unlink(path)
test("Persist + restore round-trip", t_persist)

def t_bad_version():
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tmp:
        json.dump({'version': 999}, tmp); path = tmp.name
    assert_false(KeyForge.from_env().restore_state(path))
    os.unlink(path)
test("Reject state with wrong version", t_bad_version)

end_suite()

# =============================================================================
# 6. CLOCK DRIFT
# =============================================================================
suite("Clock Drift")

def t_prev_epoch():
    now = time.time()
    t = forge.issue('internal', now=now - EPOCH_DURATION_SEC)
    r = forge.validate(t, now=now)
    assert_true(r.valid, f"Previous epoch should be valid: {r.reason}")
    assert_eq(r.drift_epochs, -1)
test("Previous epoch accepted (drift=-1)", t_prev_epoch)

def t_next_epoch():
    now = time.time()
    t = forge.issue('internal', now=now + EPOCH_DURATION_SEC)
    assert_true(forge.validate(t, now=now).valid)
test("Next epoch accepted (drift=+1)", t_next_epoch)

def t_expired():
    now = time.time()
    t = forge.issue('internal', now=now - EPOCH_DURATION_SEC * 3)
    r = forge.validate(t, now=now)
    assert_false(r.valid)
    assert_eq(r.reason, 'epoch_expired')
test("3 epochs ago rejected", t_expired)

end_suite()

# =============================================================================
# 7. SECURITY
# =============================================================================
suite("Security")

def t_diff_master():
    a = KeyForge.from_secret('alpha_secret_key_' * 3)
    b = KeyForge.from_secret('beta_secret_key__' * 3)
    r = b.validate(a.issue('internal'))
    assert_false(r.valid)
    assert_eq(r.reason, 'invalid_signature')
test("Different masters = rejection", t_diff_master)

def t_inactive_key():
    try:
        forge.issue('x', key_id='nonexistent')
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
test("Inactive key_id blocked", t_inactive_key)

end_suite()

# =============================================================================
# 8. CORTEX AUTH INTEGRATION
# =============================================================================
suite("Cortex Auth")

def t_cortex_kf():
    from backend.app.cortex import auth_class_from_token, AuthorityClass
    f = KeyForge.from_env()
    assert_eq(auth_class_from_token(f.issue('internal')), AuthorityClass.INTERNAL)
    assert_eq(auth_class_from_token(f.issue('economic')), AuthorityClass.ECONOMIC)
    assert_eq(auth_class_from_token(f.issue('orchestrator')), AuthorityClass.ORCHESTRATOR)
test("KeyForge tokens -> correct authority classes", t_cortex_kf)

def t_cortex_secrets():
    from backend.app.cortex import auth_class_from_token, AuthorityClass
    assert_eq(auth_class_from_token(os.environ['BRIDGE_INTERNAL_SECRET']), AuthorityClass.INTERNAL)
    assert_eq(auth_class_from_token(os.environ['BRIDGE_ORCHESTRATOR_SECRET']), AuthorityClass.ORCHESTRATOR)
test("Static secrets still work", t_cortex_secrets)

def t_cortex_rejects():
    from backend.app.cortex import auth_class_from_token, AuthorityClass
    for bad in [None, '', 'random', 'internal', 'orchestrator']:
        assert_eq(auth_class_from_token(bad), AuthorityClass.PUBLIC)
test("Old string bypasses blocked -> PUBLIC", t_cortex_rejects)

end_suite()

# =============================================================================
# 9. SIWE JWT
# =============================================================================
suite("SIWE JWT")

def t_siwe():
    from backend.app.services.siwe_auth import create_jwt, verify_jwt
    t = create_jwt('0xdeadbeef' * 4 + '12345678', 'economic')
    p = verify_jwt(t)
    assert_true(p is not None)
    assert_eq(p['auth'], 'economic')
test("SIWE JWT create + verify", t_siwe)

def t_siwe_expired():
    import jwt as pyjwt
    from backend.app.services.siwe_auth import JWT_SECRET
    t = pyjwt.encode({'sub': '0x1', 'exp': 1}, JWT_SECRET, algorithm='HS256')
    from backend.app.services.siwe_auth import verify_jwt
    assert_true(verify_jwt(t) is None)
test("Expired SIWE JWT rejected", t_siwe_expired)

def t_siwe_bad_key():
    import jwt as pyjwt
    t = pyjwt.encode({'sub': '0x1', 'exp': time.time() + 3600}, 'wrong' * 20, algorithm='HS256')
    from backend.app.services.siwe_auth import verify_jwt
    assert_true(verify_jwt(t) is None)
test("Wrong-key SIWE JWT rejected", t_siwe_bad_key)

end_suite()

# =============================================================================
# 10. AUDIT
# =============================================================================
suite("Audit")

def t_audit():
    f = KeyForge.from_env()
    f.issue('internal'); f.issue('economic'); f.revoke_scope('z')
    log = f.get_audit_log()
    actions = [e['action'] for e in log]
    assert_true('token_issued' in actions)
    assert_true('scope_revoked' in actions)
test("Audit log captures actions", t_audit)

def t_status():
    s = forge.status()
    assert_eq(s['version'], KEY_VERSION)
    assert_true('default' in s['active_keys'])
test("Status returns complete info", t_status)

end_suite()

# =============================================================================
# FINALIZE
# =============================================================================
finalize()
