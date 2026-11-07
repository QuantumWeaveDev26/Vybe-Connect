"""Tenant-isolated, read-only Shopify Admin GraphQL adapter (stdlib only).

No network work happens at import/status/verification time. Never logs bodies,
credentials, provider errors or order data. Callers own authentication/storage.
"""
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.request

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
_SHOP = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com", re.ASCII)
_TENANT = re.compile(r"[A-Za-z0-9_]{1,64}", re.ASCII)
_VERSION = re.compile(r"20[0-9]{2}-(?:01|04|07|10)", re.ASCII)
WEBHOOK_TOPICS = frozenset({"products/create", "products/update", "products/delete", "orders/create", "orders/updated", "orders/cancelled", "orders/paid", "orders/fulfilled", "orders/partially_fulfilled", "orders/delete", "checkouts/create", "checkouts/update", "carts/create", "carts/update"})
_PRODUCT_FIELDS = "id title handle status updatedAt"
_ORDER_FIELDS = "id name createdAt displayFinancialStatus displayFulfillmentStatus totalPriceSet { shopMoney { amount currencyCode } }"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _settings(tenant):
    if not isinstance(tenant, str) or not _TENANT.fullmatch(tenant):
        return {}
    prefix = "TW_SHOPIFY_" + tenant.upper() + "_"
    return {key.lower(): os.environ.get(prefix + key, "") for key in ("SHOP", "TOKEN", "API_VERSION", "WEBHOOK_SECRET")}


def _valid_shop(shop):
    return isinstance(shop, str) and bool(_SHOP.fullmatch(shop))


def connector_status(tenant):
    """Return environment readiness only; never proves provider credentials/scopes."""
    settings = _settings(tenant)
    shop = settings.get("shop", "")
    version = settings.get("api_version", "")
    token = settings.get("token", "")
    configured = bool(_valid_shop(shop) and _VERSION.fullmatch(version) and token and len(token) <= 4096 and not any(ord(c) < 33 or ord(c) > 126 for c in token))
    return {"configured": configured, "shop": shop if _valid_shop(shop) else None,
            "api_version": version if _VERSION.fullmatch(version) else None,
            "webhook_configured": bool(_valid_shop(shop) and settings.get("webhook_secret")),
            "live_verified": False, "read_only": True,
            "required_scopes": ["read_products", "read_orders"]}


def _failure(code, status=None):
    return {"ok": False, "items": [], "page_info": None,
            "error": {"code": code, "retryable": code in {"network_error", "rate_limited", "provider_error"}, "http_status": status}}


def _string(value, maximum=4096):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Invalid provider field")
    return value


def _normalize(kind, node):
    if not isinstance(node, dict):
        raise ValueError("Invalid node")
    identifier = _string(node.get("id"), 256)
    resource = "Product" if kind == "products" else "Order"
    if not re.fullmatch(r"gid://shopify/" + resource + r"/[0-9]+", identifier):
        raise ValueError("Invalid resource ID")
    if kind == "products":
        return {"id": identifier, "title": _string(node.get("title")), "handle": _string(node.get("handle")),
                "status": _string(node.get("status"), 64), "updated_at": _string(node.get("updatedAt"), 64)}
    money = node["totalPriceSet"]["shopMoney"]
    amount = _string(money.get("amount"), 64)
    currency = _string(money.get("currencyCode"), 3)
    if not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", amount) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Invalid money")
    return {"id": identifier, "name": _string(node.get("name")), "created_at": _string(node.get("createdAt"), 64),
            "financial_status": _string(node.get("displayFinancialStatus"), 64),
            "fulfillment_status": _string(node.get("displayFulfillmentStatus"), 64),
            "total_price": {"amount": amount, "currency_code": currency}}


def _fetch(tenant, kind, limit, cursor):
    if type(limit) is not int or not 1 <= limit <= 50 or (cursor is not None and (not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048)):
        return _failure("invalid_input")
    status = connector_status(tenant)
    if not status["configured"]:
        return _failure("not_configured")
    settings = _settings(tenant)
    fields = _PRODUCT_FIELDS if kind == "products" else _ORDER_FIELDS
    query = f"query TeamwaveRead($first: Int!, $after: String) {{ {kind}(first: $first, after: $after) {{ nodes {{ {fields} }} pageInfo {{ hasNextPage endCursor }} }} }}"
    body = json.dumps({"query": query, "variables": {"first": limit, "after": cursor}}).encode("utf-8")
    request = urllib.request.Request(f"https://{settings['shop']}/admin/api/{settings['api_version']}/graphql.json", data=body,
                                     headers={"Content-Type": "application/json", "Accept": "application/json", "X-Shopify-Access-Token": settings["token"]}, method="POST")
    # No proxies or redirects: token can only reach the validated Shopify host.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=15) as response:
            payload = response.read(MAX_PAYLOAD_BYTES + 1)
            if len(payload) > MAX_PAYLOAD_BYTES:
                return _failure("response_too_large")
            actual_version = response.headers.get("X-Shopify-API-Version")
            if actual_version != settings["api_version"]:
                return _failure("api_version_mismatch")
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            return _failure("invalid_response")
        if decoded.get("errors"):
            return _failure("graphql_error")
        connection = decoded["data"][kind]
        nodes, page_info = connection["nodes"], connection["pageInfo"]
        if not isinstance(nodes, list) or len(nodes) > limit or not isinstance(page_info, dict) or type(page_info.get("hasNextPage")) is not bool:
            return _failure("invalid_response")
        end = page_info.get("endCursor")
        if end is not None:
            _string(end, 2048)
            if not end:
                return _failure("invalid_response")
        if page_info["hasNextPage"] and not end:
            return _failure("invalid_response")
        return {"ok": True, "items": [_normalize(kind, node) for node in nodes],
                "page_info": {"has_next_page": page_info["hasNextPage"], "end_cursor": end},
                "shop": settings["shop"], "api_version": actual_version, "error": None}
    except urllib.error.HTTPError as error:
        code = "redirect_blocked" if 300 <= error.code < 400 else "unauthorized" if error.code in {401, 403} else "rate_limited" if error.code == 429 else "provider_error" if error.code >= 500 else "http_error"
        error.close()
        return _failure(code, error.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return _failure("network_error")
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return _failure("invalid_response")


def fetch_products(tenant, limit=25, cursor=None):
    """Fetch one provider page. Does not persist, loop or create Shopify records."""
    return _fetch(tenant, "products", limit, cursor)


def fetch_orders(tenant, limit=25, cursor=None):
    """Fetch one order page without customer email, phone, or address fields."""
    return _fetch(tenant, "orders", limit, cursor)


def verify_shopify_webhook(tenant, raw, headers):
    """Verify raw bytes and configured shop; caller must deduplicate delivery IDs.

    Shopify's body HMAC does not authenticate topic/shop headers themselves.
    This function imposes an exact shop match and a local topic allowlist.
    """
    settings = _settings(tenant)
    if not _valid_shop(settings.get("shop")) or not settings.get("webhook_secret") or not isinstance(raw, bytes) or len(raw) > MAX_PAYLOAD_BYTES:
        return False
    try:
        normalized = {}
        for key, value in headers.items():
            name = key.lower()
            if name in normalized or not isinstance(value, str):
                return False
            normalized[name] = value
        if normalized.get("x-shopify-shop-domain") != settings["shop"] or normalized.get("x-shopify-topic") not in WEBHOOK_TOPICS:
            return False
        signature = normalized.get("x-shopify-hmac-sha256", "")
        if len(signature) != 44:
            return False
        supplied = base64.b64decode(signature, validate=True)
        expected = hmac.new(settings["webhook_secret"].encode("utf-8"), raw, hashlib.sha256).digest()
        return hmac.compare_digest(expected, supplied)
    except (TypeError, ValueError, AttributeError, binascii.Error):
        return False
