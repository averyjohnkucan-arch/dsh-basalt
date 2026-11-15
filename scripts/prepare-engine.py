"""Install the pinned release and its isolated Python environment without starting CUDA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


def extract(archive, root):
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (root / member.name).resolve()
            if not target.is_relative_to(root.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe engine archive member")
        tar.extractall(root, filter="data")


def prepare(destination, archive=None, python=sys.executable):
    if sys.version_info < (3, 12):
        raise ValueError("Managed engine preparation requires Python 3.12 or newer")
    manifest = json.loads(Path(__file__).resolve().parents[1].joinpath("engine.json").read_text())
    if sys.platform != "linux" or os.uname().machine != "x86_64":
        raise ValueError("This plugin's managed engine targets Linux x64")
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Runtime folder already exists; choose a new empty destination")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if shutil.disk_usage(destination.parent).free < 1536 * 1024 * 1024:
        raise ValueError("Engine preparation needs at least 1.5 GiB of free disk space")
    with tempfile.TemporaryDirectory(prefix=".basalt-setup-", dir=destination.parent) as temp:
        temp = Path(temp)
        pack = Path(archive).resolve() if archive else temp / "engine.tar.gz"
        if not archive:
            print("Downloading Basalt " + manifest["version"], flush=True)
            with urllib.request.urlopen(manifest["url"], timeout=120) as response, pack.open("wb") as out:
                shutil.copyfileobj(response, out)
        with pack.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest != manifest["sha256"]:
            raise ValueError("Engine archive SHA-256 mismatch")
        extracted = temp / "unpack"
        extracted.mkdir()
        extract(pack, extracted)
        source = extracted / ("basalt-v" + manifest["version"] + "-linux-x64")
        if not source.joinpath("bin/basalt").is_file():
            raise ValueError("Engine archive has no Basalt executable")
        # A venv contains absolute paths: create it only at its final location.
        source.rename(destination)
    try:
        subprocess.run([python, "-m", "venv", str(destination / ".venv")], check=True)
        subprocess.run([str(destination / ".venv/bin/python"), "-m", "pip", "install", "--no-cache-dir", "--only-binary=:all:", "-r", str(destination / "requirements.txt"), "nvidia-cuda-runtime==13.0.96", "nvidia-cublas==13.0.2.14"], check=True)
        subprocess.run([str(destination / ".venv/bin/python"), "-m", "pip", "check"], check=True)
        libraries = sorted({str(p.parent.relative_to(destination)) for p in destination.glob(".venv/lib/python*/site-packages/nvidia/**/libc*.so.13")})
        if not libraries:
            raise ValueError("CUDA 13 runtime libraries were not installed")
        destination.joinpath("dsh-engine.json").write_text(json.dumps({**manifest, "libraryDirs": libraries}, indent=2) + "\n")
    except BaseException:
        shutil.rmtree(destination)
        raise
    print("Prepared " + str(destination) + "; no model or CUDA was started", flush=True)


if __name__ == "__main__":
    def cancelled(_signum, _frame):
        raise KeyboardInterrupt("Engine preparation cancelled")
    signal.signal(signal.SIGTERM, cancelled)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--archive")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    prepare(args.destination, args.archive, args.python)
