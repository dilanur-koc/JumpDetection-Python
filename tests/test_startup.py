"""Model ve kamera gerektirmeyen baslatma kontrolleri."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jump_detection import app


ROOT = Path(__file__).resolve().parent.parent


class StartupTests(unittest.TestCase):
    def test_imports_do_not_load_camera_dependencies(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import main; import jump_detection.app; "
                "assert 'cv2' not in sys.modules; "
                "assert 'mediapipe' not in sys.modules",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_model_path_does_not_depend_on_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); "
                    "from jump_detection.config import MODEL_PATH; "
                    "print(MODEL_PATH)",
                    str(ROOT),
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), ROOT / "pose_landmarker_lite.task")

    def test_missing_model_exits_before_camera_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.task"
            with patch.object(app, "MODEL_PATH", missing):
                with self.assertRaisesRegex(SystemExit, "model dosyasi bulunamadi"):
                    app.main()


if __name__ == "__main__":
    unittest.main()
