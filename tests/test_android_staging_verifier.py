from pathlib import Path

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
