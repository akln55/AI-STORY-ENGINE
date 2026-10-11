from io import BytesIO
from pathlib import Path
import tarfile
import zipfile

from tools.verify_android_staging import verify_staging


def test_staging_verifier_accepts_matching_critical_files(tmp_path: Path):
    source = tmp_path / "source"
    staging = tmp_path / "build" / "android" / "app"
    for rel, content in {
        "main.py": "from rpg_android_app import RPGEngineApp\n",
        "rpg_android_app.py": "print(1)\n",
        "rpg_android_file_picker.py": "print(2)\n",
    }.items():
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (staging / rel).parent.mkdir(parents=True, exist_ok=True)
        (source / rel).write_text(content, encoding="utf-8")
        (staging / rel).write_text(content, encoding="utf-8")

    assert verify_staging(source, staging) == []


def test_staging_verifier_rejects_stale_main(tmp_path: Path):
    source = tmp_path / "source"
    staging = tmp_path / "build" / "android" / "app"
    for rel in ("main.py", "rpg_android_app.py", "rpg_android_file_picker.py"):
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (staging / rel).parent.mkdir(parents=True, exist_ok=True)
    (source / "main.py").write_text("from rpg_android_app import RPGEngineApp\n", encoding="utf-8")
    (staging / "main.py").write_text("from android.main import RPGEngineApp\n", encoding="utf-8")
    for rel in ("rpg_android_app.py", "rpg_android_file_picker.py"):
        content = "print(1)\n"
        (source / rel).write_text(content, encoding="utf-8")
        (staging / rel).write_text(content, encoding="utf-8")

    errors = verify_staging(source, staging)
    assert any("hash mismatch for main.py" in error for error in errors)
    assert any("android.main" in error for error in errors)


def test_apk_verifier_ignores_itself_when_scanning_for_forbidden_imports(tmp_path: Path):
    from tools.verify_android_staging import verify_apk

    source = tmp_path / "source"
    for rel, content in {
        "main.py": "from rpg_android_app import RPGEngineApp\n",
        "rpg_android_app.py": "print(1)\n",
        "rpg_android_file_picker.py": "print(2)\n",
        "tools/verify_android_staging.py": "FORBIDDEN = 'android.main'\n",
    }.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    apk = tmp_path / "app.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        for rel in ("main.py", "rpg_android_app.py", "rpg_android_file_picker.py", "tools/verify_android_staging.py"):
            archive.writestr(f"assets/private/{rel}", (source / rel).read_bytes())

    assert verify_apk(source, apk) == []


def test_apk_content_verifier_accepts_python_for_android_private_tar(tmp_path: Path):
    from tools.verify_android_staging import verify_apk

    source = tmp_path / "source"
    payloads = {
        "main.py": "from rpg_android_app import RPGEngineApp\n",
        "rpg_android_app.py": "print('app')\n",
        "rpg_android_file_picker.py": "print('picker')\n",
    }
    for rel, content in payloads.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    tar_bytes = BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as private:
        for rel in payloads:
            private.add(source / rel, arcname=rel)

    apk = tmp_path / "app.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("assets/private.tar", tar_bytes.getvalue())

    assert verify_apk(source, apk) == []
