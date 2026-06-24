# ClashTX TUN Tools

Project-local helpers for Mihomo TUN mode on Linux.

- `ensure-tun.sh` — ensures `/dev/net/tun` exists (loads `tun` module when possible)
- `grant-caps.sh` — grants `CAP_NET_ADMIN` to the bundled Mihomo binary (requires sudo once)
- Mihomo core itself lives in `vendor/mihomo/` and handles the TUN interface

TUN mode requires the Mihomo process to run with network capabilities. Run once:

```bash
./vendor/tun/grant-caps.sh
```

Or manually:

```bash
sudo setcap cap_net_admin,cap_net_bind_service+ep vendor/mihomo/verge-mihomo
```

After updating the Mihomo core, run `grant-caps.sh` again.
