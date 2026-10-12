from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"
BUILDOZER_SPEC = ROOT / "buildozer.spec"
ANDROID_WORKFLOW = ROOT / ".github" / "workflows" / "android-build.yml"


def test_gitignore_excludes_environment_secrets_and_signing_material():
    ignored = set(GITIGNORE.read_text(encoding="utf-8").splitlines())

    required = {
        ".env",
        ".env.*",
        "!.env.example",
        ".envrc",
        ".direnv/",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "*.jks",
        "*.keystore",
        "*.p8",
        "*.mobileprovision",
        "*.provisionprofile",
        "*.secret",
        "*.token",
        "*credentials*.json",
        "*service-account*.json",
    }
    assert required <= ignored


def test_gitignore_keeps_local_runtime_data_and_models_out_of_git():
    ignored = set(GITIGNORE.read_text(encoding="utf-8").splitlines())
    assert {"saves/", "imports/", "models/", "logs/", "*.gguf", "*.apk", "*.aab"} <= ignored


def test_android_package_allowlist_does_not_include_env_or_secret_extensions():
    spec = BUILDOZER_SPEC.read_text(encoding="utf-8")
    include_line = next(line for line in spec.splitlines() if line.startswith("source.include_exts = "))
    extensions = set(include_line.split("=", 1)[1].strip().split(","))

    assert "env" not in extensions
    assert "secret" not in extensions
    assert "token" not in extensions
    assert "pem" not in extensions
    assert "key" not in extensions
    assert "p8" not in extensions
    assert "p12" not in extensions


def test_android_build_does_not_receive_provider_credentials():
    workflow = ANDROID_WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in workflow
    assert "persist-credentials: false" in workflow
    assert "permissions:\n  contents: read" in workflow
