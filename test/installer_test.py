import importlib.util
from pathlib import Path
import io
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("prepare_engine", Path(__file__).resolve().parents[1] / "scripts/prepare-engine.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ArchiveSafety(unittest.TestCase):
    def test_rejects_traversal_and_links(self):
        for name, kind in [("../outside", tarfile.REGTYPE), ("bad", tarfile.SYMTYPE), ("/absolute", tarfile.REGTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                pack = root / "engine.tar.gz"
                with tarfile.open(pack, "w:gz") as tar:
                    entry = tarfile.TarInfo(name)
                    entry.type = kind
                    entry.linkname = "/etc/passwd"
                    tar.addfile(entry)
                with self.assertRaises(ValueError):
                    installer.extract(pack, root / "out")

    def test_safe_archive_extracts(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            pack = root / "engine.tar.gz"
            with tarfile.open(pack, "w:gz") as tar:
                entry = tarfile.TarInfo("engine/file")
                entry.size = 2
                tar.addfile(entry, io.BytesIO(b"ok"))
            installer.extract(pack, root / "out")
            self.assertEqual((root / "out/engine/file").read_bytes(), b"ok")

    def test_checksum_failure_leaves_no_runtime(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            pack = root / "bad.tar.gz"
            pack.write_bytes(b"wrong")
            with patch.object(installer.shutil, "disk_usage", return_value=SimpleNamespace(free=10**12)):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    installer.prepare(root / "runtime", pack)
            self.assertFalse((root / "runtime").exists())
