import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mermaid2image.py"
SPEC = importlib.util.spec_from_file_location("mermaid2image_script", SCRIPT_PATH)
mermaid2image = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mermaid2image)


class Mermaid2ImageSecretTests(unittest.TestCase):
    def test_mermaid_blocks_replace_sensitive_keys_with_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(
                """# Secret Flow

```mermaid
flowchart TD
  A["IMAGEKIT_PRIVATE_KEY=private_live_1234567890"]
  B["IMAGEKIT_PUBLIC_KEY='public_live_abcdef'"]
  C["-----BEGIN PRIVATE KEY-----
abc123
-----END PRIVATE KEY-----"]
```
"""
            )

            def fake_render(source: Path, output: Path, width: int, scale: float) -> None:
                output.write_bytes(b"png")

            with (
                mock.patch.object(mermaid2image, "render_mermaid", side_effect=fake_render),
                mock.patch.object(sys, "argv", ["mermaid2image.py", str(article), "--no-replace"]),
            ):
                self.assertEqual(mermaid2image.main(), 0)

            mmd_text = (Path(tmp) / "images" / "01-secret-flow.mmd").read_text()
            self.assertIn("IMAGEKIT_PRIVATE_KEY=${IMAGEKIT_PRIVATE_KEY}", mmd_text)
            self.assertIn("IMAGEKIT_PUBLIC_KEY='${IMAGEKIT_PUBLIC_KEY}'", mmd_text)
            self.assertIn("${PRIVATE_KEY}", mmd_text)
            self.assertNotIn("private_live_1234567890", mmd_text)
            self.assertNotIn("public_live_abcdef", mmd_text)
            self.assertNotIn("abc123", mmd_text)


if __name__ == "__main__":
    unittest.main()
