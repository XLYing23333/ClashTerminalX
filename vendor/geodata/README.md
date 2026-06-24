# Bundled Geodata

ClashTX ships Mihomo geodata files so first startup does not depend on GitHub downloads.

| File | Purpose |
| --- | --- |
| `geoip.metadb` | `GEOIP,...` rules |
| `geosite.dat` | `GEOSITE,...` rules |

Source: [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)

Refresh locally:

```bash
./scripts/fetch-geodata.sh
```
