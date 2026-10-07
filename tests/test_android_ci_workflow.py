from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "android-build.yml"
NATIVE_BUILD = ROOT / "tools" / "build_llama_server_android.sh"
SPEC = ROOT / "buildozer.spec"


def test_android_ci_workflow_is_security_pinned_and_read_only():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "runs-on: ubuntu-24.04" in text
    assert "timeout-minutes: 60" in text
    assert "permissions:\n  contents: read" in text
    assert "secrets." not in text
    assert "persist-credentials: false" in text

    use_lines = re.findall(r"^\s+uses:\s+([^\s]+)", text, flags=re.MULTILINE)
    assert use_lines, "workflow must use at least one GitHub Action"
    for ref in use_lines:
        assert re.search(r"@[0-9a-f]{40}$", ref), f"unpinned action reference: {ref}"


def test_android_ci_workflow_has_deterministic_native_and_build_paths():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'NDK_VERSION: "29.0.14206865"' in text
    assert 'source "$VENV_DIR/bin/activate"' in text
    assert 'test "$VIRTUAL_ENV" = "$VENV_DIR"' in text
    assert 'export PATH="$VENV_DIR/bin:$PATH"' in text
    assert "command -v cython" in text
    assert "cython --version" in text
    assert "command -v buildozer" in text
    assert "android_native/arm64-v8a/llama-server.bin" in text
    assert 'name: rpg-engine-v1.1.4-android-debug' in text
    assert '${{ env.BIN_DIR }}/*.apk' in text
    assert "package: name='org.rpgengine'" in text
    assert "p4a_commit=58d21141f17c889bf8585f5665921d72028f8831" in text
    spec = SPEC.read_text(encoding="utf-8")
    assert "package.domain = org" in spec
    assert "build_dir = ./.ci/build-cache" in spec
    assert "bin_dir = ./.ci/bin" in spec
    assert "./android_native/arm64-v8a/llama-server.bin --version" not in text


def test_native_build_script_is_real_checkout_and_fully_pinned():
    text = NATIVE_BUILD.read_text(encoding="utf-8")
    assert "--no-checkout" not in text
    assert 'LLAMA_TAG="v0.6.0"' in text
    assert 'LLAMA_COMMIT="d81235049384534c167caea52b85a694f6103d14"' in text
    assert 'git clone --filter=blob:none --depth 1 --branch "$LLAMA_TAG"' in text
    assert 'test "$ACTUAL_COMMIT" = "$LLAMA_COMMIT"' in text
    assert '"$OUT" --version' not in text


def test_buildozer_p4a_is_pinned_to_stable_release():
    text = SPEC.read_text(encoding="utf-8")
    assert "p4a.branch = master" in text
    assert "p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831" in text


def test_test_only_workflow_is_read_only_and_action_pinned():
    text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "permissions:\n  contents: read" in text
    assert "runs-on: ubuntu-24.04" in text
    assert "pytest==8.4.2" in text
    use_lines = re.findall(r"^\s+uses:\s+([^\s]+)", text, flags=re.MULTILINE)
    assert use_lines
    for ref in use_lines:
        assert re.search(r"@[0-9a-f]{40}$", ref), f"unpinned action reference: {ref}"


def test_android_workflow_verifies_staged_source_before_apk_metadata():
    source = (ROOT / ".github" / "workflows" / "android-build.yml").read_text()
    assert "tools/verify_android_staging.py" in source
    assert "rpg-engine-v1.1.4-android-debug" in source
