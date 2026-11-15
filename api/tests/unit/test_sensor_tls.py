"""TLS lifecycle tests use only synthetic keys in pytest temporary directories."""
import importlib.util
import ipaddress
from pathlib import Path
import ssl

from cryptography import x509
import pytest


@pytest.fixture
def provision():
    path = Path(__file__).resolve().parents[3] / "sensor_agent/provision_tls.py"
    spec = importlib.util.spec_from_file_location("unit_tls_provision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.provision


def test_provision_has_correct_identity_chain_and_ten_year_lifetime(tmp_path, provision):
    provision(tmp_path, "192.0.2.10")
    ca = x509.load_pem_x509_certificate((tmp_path / "ca.crt").read_bytes())
    cert = x509.load_pem_x509_certificate((tmp_path / "server.crt").read_bytes())
    cert.verify_directly_issued_by(ca)
    assert cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress) == [ipaddress.ip_address("192.0.2.10")]
    assert 3649 <= (cert.not_valid_after_utc - cert.not_valid_before_utc).days <= 3651
    assert not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    context = ssl.create_default_context(cafile=str(tmp_path / "ca.crt"))
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED


def test_rerun_preserves_keys_and_renewal_preserves_ca(tmp_path, provision):
    provision(tmp_path, "192.0.2.10")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    provision(tmp_path, "192.0.2.10")
    assert all(p.read_bytes() == value for p, value in before.items())
    with pytest.raises(ValueError, match="IP changed"):
        provision(tmp_path, "192.0.2.11")
    provision(tmp_path, "192.0.2.11", renew=True)
    assert (tmp_path / "ca.crt").read_bytes() == before[tmp_path / "ca.crt"]
    assert (tmp_path / "private/ca.key").read_bytes() == before[tmp_path / "private/ca.key"]
    assert (tmp_path / "server.key").read_bytes() != before[tmp_path / "server.key"]


def test_incomplete_or_mismatched_installation_is_not_silently_replaced(tmp_path, provision):
    provision(tmp_path, "192.0.2.10")
    ca = (tmp_path / "ca.crt").read_bytes()
    (tmp_path / "server.key").write_bytes((tmp_path / "private/ca.key").read_bytes())
    with pytest.raises(ValueError, match="do not match"):
        provision(tmp_path, "192.0.2.10")
    (tmp_path / "server.key").unlink()
    with pytest.raises(ValueError, match="Incomplete"):
        provision(tmp_path, "192.0.2.10")
    assert (tmp_path / "ca.crt").read_bytes() == ca


def test_remote_configuration_fails_fast_for_http_missing_or_bad_trust(tmp_path, unit_ca):
    import ast
    from app.core.config import settings as unit_settings
    # Execute the actual Settings definition without its production startup/.env load.
    path = Path(__file__).resolve().parents[2] / "app/core/config.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef))]
    scope = {"ROOT_DIR": tmp_path, "ENV_PATH": tmp_path / "unused.env", "__name__": "unit_settings_definition"}
    exec(compile(tree, str(path), "exec"), scope)
    values = dict(vars(unit_settings), SENSOR_CA_CERT=unit_ca)
    Settings = scope["Settings"]
    valid = Settings(_env_file=None, **values)
    assert valid.SENSOR_CA_CERT == unit_ca
    for overrides in ({"SENSOR_AGENT_URL": "http://sensor.invalid"},
                      {"SENSOR_CA_CERT": ""}, {"SENSOR_CA_CERT": str(tmp_path / "missing.crt")},
                      {"SENSOR_AGENT_URL": "https://user:pass@sensor.invalid"},
                      {"SENSOR_AGENT_URL": "https://sensor.invalid/path"}):
        with pytest.raises((ValueError, OSError)):
            Settings(_env_file=None, **(values | overrides))
    mock = Settings(_env_file=None, **(values | {"SENSOR_MOCK_MODE": True, "SENSOR_CA_CERT": ""}))
    assert mock.SENSOR_MOCK_MODE
