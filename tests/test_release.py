import tempfile
import unittest
from pathlib import Path

from scripts.release_tools import build, files, packages, restore


class ReleaseTests(unittest.TestCase):
    def test_rejects_unsafe_snapshot_ids(self):
        for name in ("../main", "/tmp/x", "a b", "x;echo", "", "x" * 81):
            with self.subTest(name=name), self.assertRaises(ValueError):
                files.validate_snapshot_id(name)

    def test_source_fingerprint_changes_with_bytes_and_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "a.R"
            file.write_text("x <- 1\n")
            original = packages.package_source_digest(root)
            self.assertEqual(original, packages.package_source_digest(root))
            file.write_text("x <- 2\n")
            self.assertNotEqual(original, packages.package_source_digest(root))
            file.write_text("x <- 1\n")
            file.rename(root / "b.R")
            self.assertNotEqual(original, packages.package_source_digest(root))

    def test_dependency_order(self):
        ordered = [
            fields["Package"]
            for _, fields in packages.packages_in_dependency_order(build.ROOT)
        ]
        self.assertLess(ordered.index("tb.checks"), ordered.index("tb.modules"))
        self.assertLess(ordered.index("tb.reporter"), ordered.index("tb.modules"))
        self.assertLess(ordered.index("tb.modules"), ordered.index("tb.builder"))

    def test_dependency_cycle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, dep in (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")):
                directory = root / "packages" / name
                directory.mkdir(parents=True)
                (directory / "DESCRIPTION").write_text(
                    f"Package: {name}\nVersion: 1.0.0\nImports: {dep}\n"
                )
            with self.assertRaisesRegex(ValueError, "cycle"):
                packages.packages_in_dependency_order(root)

    def test_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "already exists"):
                build.build_snapshot(tmp, "example", "https://example.org", "a" * 40)

    def test_existing_archive_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshots" / "example"
            snapshot.mkdir(parents=True)
            (snapshot / "package.tar.gz").write_bytes(b"bad bytes")
            files.write_json(
                snapshot / "release.json",
                {
                    "packages": [
                        {
                            "name": "pkg",
                            "version": "1.0.0",
                            "file": "package.tar.gz",
                            "sha256": "0" * 64,
                        }
                    ]
                },
            )
            with self.assertRaisesRegex(ValueError, "checksum"):
                packages.read_published_packages(tmp)

    def test_release_lock_does_not_modify_source_lock(self):
        original = {
            "R": {"Repositories": [{"Name": "CRAN", "URL": "https://example.org"}]},
            "Packages": {},
        }
        result = build.release_lockfile(
            original,
            [{"name": "tb.example", "version": "1.0.0"}],
            "https://example.org/snapshots/one",
        )
        self.assertEqual(original["Packages"], {})
        self.assertEqual(len(original["R"]["Repositories"]), 1)
        self.assertEqual(result["Packages"]["tb.example"]["Repository"], "TBDEMO")

    def test_restore_must_use_the_project_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "project library"):
                restore.find_restored_library(Path(temporary))


if __name__ == "__main__":
    unittest.main()
