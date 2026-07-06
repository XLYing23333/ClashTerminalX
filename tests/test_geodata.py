import os

from clashtx.core.geodata import BUNDLED_GEODATA_DIR, ensure_geodata


def test_ensure_geodata_copies_bundled_files(tmp_path):
    config_dir = tmp_path / "config"
    installed = ensure_geodata(config_dir)

    assert BUNDLED_GEODATA_DIR.is_dir()
    assert (config_dir / "geoip.metadb").exists()
    assert (config_dir / "geosite.dat").exists()
    assert len(installed) == 2


def test_ensure_geodata_skips_when_runtime_is_newer(tmp_path):
    config_dir = tmp_path / "config"
    ensure_geodata(config_dir)

    geoip = config_dir / "geoip.metadb"
    geoip.write_bytes(b"cached")
    future = geoip.stat().st_mtime + 3600
    os.utime(geoip, (future, future))

    ensure_geodata(config_dir)
    assert geoip.read_bytes() == b"cached"
