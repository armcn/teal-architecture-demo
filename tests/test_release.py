import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("release", Path(__file__).parents[1] / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_rejects_unsafe_snapshot_ids(self):
        for name in ("../main", "/tmp/x", "a b", "x;echo", "", "x" * 81):
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.validate_id(name)

    def test_source_fingerprint_changes_with_bytes_and_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "a.R"
            file.write_text("x <- 1\n")
            original = release.source_hash(root)
            self.assertEqual(original, release.source_hash(root))
            file.write_text("x <- 2\n")
            self.assertNotEqual(original, release.source_hash(root))
            file.write_text("x <- 1\n")
            file.rename(root / "b.R")
            self.assertNotEqual(original, release.source_hash(root))

    def test_dependency_order(self):
        ordered = [fields["Package"] for _, fields in release.package_order(release.ROOT)]
        self.assertLess(ordered.index("tb.checks"), ordered.index("tb.modules"))
        self.assertLess(ordered.index("tb.reporter"), ordered.index("tb.modules"))
        self.assertLess(ordered.index("tb.modules"), ordered.index("tb.builder"))

    def test_dependency_cycle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, dep in (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")):
                directory = root / "packages" / name
                directory.mkdir(parents=True)
                (directory / "DESCRIPTION").write_text(f"Package: {name}\nVersion: 1.0.0\nImports: {dep}\n")
            with self.assertRaisesRegex(ValueError, "cycle"):
                release.package_order(root)

    def test_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "already exists"):
                release.build(tmp, "example", "https://example.org", "a" * 40)

    def test_existing_archive_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshots" / "example"
            snapshot.mkdir(parents=True)
            (snapshot / "package.tar.gz").write_bytes(b"bad bytes")
            release.write_json(snapshot / "release.json", {"packages": [{"name": "pkg", "version": "1.0.0", "file": "package.tar.gz", "sha256": "0" * 64}]})
            with self.assertRaisesRegex(ValueError, "checksum"):
                release.prior_packages(tmp)


if __name__ == "__main__":
    unittest.main()
