#!/usr/bin/env python3
"""Make the apps' signing key once, on your own computer, for the repository's secrets.

The key signs both APKs; Android only installs an update signed with the same key, so keep the file and the
password it prints somewhere safe (a password manager). It is written to your home folder, outside the repo, and
must never be committed.

  pip install cryptography
  python .github/tools/make_signing_key.py

With GitHub CLI installed and signed in (`gh auth login`), it stores both secrets in the repository itself and
prints nothing secret. Without it, it prints them, for GitHub: the repository → Settings → Secrets and variables →
Actions → New repository secret, twice:
  ANDROID_KEYSTORE_B64       the long text it prints
  ANDROID_KEYSTORE_PASSWORD  the password it prints
The builds sign with it from then on (CI refuses to build without it). TVs that have apps signed with another
key need them installed again once (optimize/install.sh does that by itself; their settings start over).
"""
import base64
import datetime
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

ALIAS = b"caftv"   # android/*/build.gradle signs with this alias
REPO = "iT-CAF/CAF-TV"


def make(password):
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CAF TV"), x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CAF TV")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365 * 100))   # Android wants it valid long after the last update
            .sign(key, hashes.SHA256()))
    return pkcs12.serialize_key_and_certificates(ALIAS, key, cert, None,
                                                 serialization.BestAvailableEncryption(password.encode()))


def main():
    out = Path.home() / "caftv-signing-key.p12"
    if out.exists():
        sys.exit(f"{out} already exists: that is your key. Use it, or move it away first to make a new one.")
    password = secrets.token_urlsafe(30)
    data = make(password)
    out.write_bytes(data)
    (Path.home() / "caftv-signing-key-password.txt").write_text(password + "\n")
    print(f"Key saved to {out}, its password to {Path.home() / 'caftv-signing-key-password.txt'}")
    print("Keep both somewhere safe (a password manager, a USB stick); never commit them.\n")
    secret = {"ANDROID_KEYSTORE_B64": base64.b64encode(data).decode(), "ANDROID_KEYSTORE_PASSWORD": password}
    gh = gh_ready()
    if gh:
        for name, value in secret.items():   # the value goes in on stdin, never on the command line
            subprocess.run([gh, "secret", "set", name, "--repo", REPO], input=value, text=True, check=True)
        print(f"Both secrets are now in {REPO}. The next build signs with this key.")
        return
    print("GitHub CLI isn't signed in, so add these two secrets by hand (see the top of this file):\n")
    for name, value in secret.items():
        print(f"{name}:\n{value}\n")


def gh_ready():
    """GitHub CLI's path if it is installed and signed in, else None."""
    gh = shutil.which("gh")
    return gh if gh and subprocess.run([gh, "auth", "status"], capture_output=True).returncode == 0 else None


if __name__ == "__main__":
    main()
