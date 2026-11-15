"""Provision installation-specific CA and server certificates; never export keys."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def provision(directory: Path, host: str, renew: bool = False):
    address = ipaddress.ip_address(host)
    now = datetime.now(timezone.utc)
    directory.mkdir(mode=0o750, parents=True, exist_ok=True)
    private = directory / "private"
    private.mkdir(mode=0o700, exist_ok=True)
    paths = [private / "ca.key", directory / "ca.crt", directory / "server.key", directory / "server.crt"]
    if any(p.is_symlink() for p in [directory, private, *paths]):
        raise ValueError("TLS paths must not be symlinks.")
    if any(p.exists() for p in paths) and not all(p.is_file() for p in paths):
        raise ValueError("Incomplete TLS installation; restore its backup before provisioning.")
    if all(p.is_file() for p in paths):
        ca_key = serialization.load_pem_private_key(paths[0].read_bytes(), password=None)
        ca = x509.load_pem_x509_certificate(paths[1].read_bytes())
        cert = x509.load_pem_x509_certificate(paths[3].read_bytes())
        server_key = serialization.load_pem_private_key(paths[2].read_bytes(), password=None)
        if ca_key.public_key().public_numbers() != ca.public_key().public_numbers():
            raise ValueError("CA certificate and key do not match.")
        ca.verify_directly_issued_by(ca)
        cert.verify_directly_issued_by(ca)
        if server_key.public_key().public_numbers() != cert.public_key().public_numbers():
            raise ValueError("Server certificate and key do not match.")
        if ca.not_valid_after_utc <= now + timedelta(days=30):
            raise ValueError("CA expires soon; explicitly replace CA and redistribute public trust.")
        if not renew:
            if address not in cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress):
                raise ValueError("Management IP changed; rerun with --renew and the new IP.")
            if cert.not_valid_before_utc > now or cert.not_valid_after_utc <= now + timedelta(days=30):
                raise ValueError("Server certificate needs renewal; rerun with --renew.")
            return
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AI NIDS installation CA")])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
              .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=3651))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
              .sign(ca_key, hashes.SHA256()))
        write_key(paths[0], ca_key)
        paths[1].write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(min(now + timedelta(days=3650), ca.not_valid_after_utc))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))
    write_key(paths[2], key)
    paths[3].write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def write_key(path, key):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--host", required=True, help="Management IPv4/IPv6 address")
    parser.add_argument("--renew", action="store_true", help="Renew server certificate under the existing CA")
    args = parser.parse_args()
    provision(args.directory, args.host, args.renew)
