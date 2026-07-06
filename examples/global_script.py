"""Example ClashTX global runtime config script.

Copy this file to `.runtime/config/global_script.py` and edit it as needed.
The script is applied every time ClashTX generates `mihomo.yaml`.

Replace the placeholder domains and IPs below with your own values before use.
"""

from __future__ import annotations

from typing import Any


def main(config: dict[str, Any]) -> dict[str, Any]:
    rules = config.setdefault("rules", [])

    prepend_rules = [
        "DOMAIN-SUFFIX,example.com,DIRECT",
        "DOMAIN-SUFFIX,example.org,DIRECT",
        "DOMAIN-SUFFIX,example.net,DIRECT",
        "IP-CIDR,203.0.113.10/32,DIRECT,no-resolve",
        "IP-CIDR,203.0.113.11/32,DIRECT,no-resolve",
    ]

    config["rules"] = [
        *[rule for rule in prepend_rules if rule not in rules],
        *rules,
    ]

    dns = config.setdefault("dns", {})
    fake_ip_filter = dns.setdefault("fake-ip-filter", [])

    additions = [
        "example.com",
        "*.example.com",
        "+.example.com",
        "example.org",
        "*.example.org",
        "+.example.org",
        "example.net",
        "*.example.net",
        "+.example.net",
        "203.0.113.10",
        "203.0.113.11",
    ]

    dns["fake-ip-filter"] = list(dict.fromkeys([*fake_ip_filter, *additions]))

    return config
