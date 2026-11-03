import base64
import hashlib
import hmac
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import shopify_connector as connector


ENV = {"TW_SHOPIFY_DEMO_SHOP": "example.myshopify.com", "TW_SHOPIFY_DEMO_TOKEN": "synthetic-token",
       "TW_SHOPIFY_DEMO_API_VERSION": "2026-10", "TW_SHOPIFY_DEMO_WEBHOOK_SECRET": "synthetic-secret"}


class Response(io.BytesIO):
    def __init__(self, payload, version="2026-10"):
        super().__init__(json.dumps(payload).encode())
        self.headers = {"X-Shopify-API-Version": version}
        self.status = 200


def page(kind="products", nodes=None, more=False, cursor=None):
    return {"data": {kind: {"nodes": nodes or [], "pageInfo": {"hasNextPage": more, "endCursor": cursor}}}}


class ShopifyTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def transport(self, response):
        return patch("shopify_connector.urllib.request.OpenerDirector.open", return_value=response)

    def test_status_does_not_expose_credentials_or_claim_connection(self):
        result = connector.connector_status("demo")
        self.assertTrue(result["configured"])
        self.assertFalse(result["live_verified"])
        self.assertNotIn("synthetic", json.dumps(result))

    def test_rejects_unconfigured_and_cross_tenant_settings(self):
        self.assertFalse(connector.connector_status("other")["configured"])
        self.assertEqual(connector.fetch_orders("other")["error"]["code"], "not_configured")

    def test_rejects_arbitrary_egress_and_ambiguous_tenant(self):
        for shop in ("https://example.myshopify.com", "example.com", "a.myshopify.com.evil.test", "a.myshopify.com:443", "a.b.myshopify.com", "127.0.0.1", "a.myshopify.com/", "-a.myshopify.com"):
            with self.subTest(shop=shop), patch.dict(os.environ, {"TW_SHOPIFY_DEMO_SHOP": shop}):
                self.assertFalse(connector.connector_status("demo")["configured"])
        self.assertFalse(connector.connector_status("demo-other")["configured"])

    def test_requires_explicit_quarterly_api_version(self):
        for version in ("", "latest", "2026-11", "2026-10/../../"):
            with self.subTest(version=version), patch.dict(os.environ, {"TW_SHOPIFY_DEMO_API_VERSION": version}):
                self.assertFalse(connector.connector_status("demo")["configured"])

    def test_products_use_read_query_and_actual_provider_pagination(self):
        product = {"id": "gid://shopify/Product/1", "title": "Example", "handle": "example", "status": "ACTIVE", "updatedAt": "2026-10-29T00:00:00Z", "private": "drop"}
        with self.transport(Response(page(nodes=[product], more=True, cursor="next"))) as opening:
            result = connector.fetch_products("demo", 2, "previous")
        self.assertTrue(result["ok"])
        self.assertEqual(result["page_info"], {"has_next_page": True, "end_cursor": "next"})
        self.assertEqual(result["items"][0]["id"], "gid://shopify/Product/1")
        self.assertNotIn("private", result["items"][0])
        request = opening.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.myshopify.com/admin/api/2026-10/graphql.json")
        body = json.loads(request.data)
        self.assertEqual(body["variables"], {"first": 2, "after": "previous"})
        self.assertTrue(body["query"].startswith("query "))
        self.assertNotIn("mutation", body["query"])

    def test_orders_exclude_customer_address_email_and_preserve_money_strings(self):
        order = {"id": "gid://shopify/Order/2", "name": "#2", "createdAt": "2026-10-29T00:00:00Z", "displayFinancialStatus": "PAID", "displayFulfillmentStatus": "UNFULFILLED", "totalPriceSet": {"shopMoney": {"amount": "12.30", "currencyCode": "USD"}}, "email": "private@example.test"}
        with self.transport(Response(page("orders", [order]))) as opening:
            result = connector.fetch_orders("demo")
        self.assertTrue(result["ok"])
        self.assertEqual(result["items"][0]["total_price"], {"amount": "12.30", "currency_code": "USD"})
        self.assertNotIn("email", json.dumps(result))
        query = json.loads(opening.call_args.args[0].data)["query"]
        self.assertNotIn("customer", query)

    def test_invalid_inputs_return_errors_without_network(self):
        for limit in (0, 51, True, "25", None):
            self.assertEqual(connector.fetch_products("demo", limit)["error"]["code"], "invalid_input")
        self.assertEqual(connector.fetch_products("demo", cursor="x" * 2049)["error"]["code"], "invalid_input")

    def test_provider_errors_are_redacted_and_partial_data_rejected(self):
        with self.transport(Response({"data": page()["data"], "errors": [{"message": "synthetic-token private@example.test"}]})):
            result = connector.fetch_products("demo")
        self.assertEqual(result["error"]["code"], "graphql_error")
        self.assertNotIn("synthetic", json.dumps(result))
        self.assertEqual(result["items"], [])

    def test_malformed_and_oversized_provider_responses_fail_closed(self):
        for payload in ({}, {"data": {"products": {"nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": None}}}}, {"data": {"products": {"nodes": [None], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}):
            with self.transport(Response(payload)):
                self.assertEqual(connector.fetch_products("demo")["error"]["code"], "invalid_response")
        with self.transport(io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))):
            self.assertEqual(connector.fetch_products("demo")["error"]["code"], "response_too_large")

    def test_version_fall_forward_is_rejected(self):
        with self.transport(Response(page(), version="2027-01")):
            self.assertEqual(connector.fetch_products("demo")["error"]["code"], "api_version_mismatch")

    def test_transport_http_and_rate_limit_failures(self):
        for exception, code in [(URLError("synthetic-token"), "network_error"), (HTTPError("", 401, "private", {}, None), "unauthorized"), (HTTPError("", 429, "private", {}, None), "rate_limited"), (HTTPError("", 302, "private", {}, None), "redirect_blocked")]:
            with patch("shopify_connector.urllib.request.OpenerDirector.open", side_effect=exception):
                result = connector.fetch_orders("demo")
                self.assertEqual(result["error"]["code"], code)
                self.assertNotIn("synthetic", json.dumps(result))

    def test_redirect_handler_never_forwards_token(self):
        request = connector.urllib.request.Request("https://example.myshopify.com", headers={"X-Shopify-Access-Token": "synthetic"})
        handler = connector._NoRedirect()
        self.assertIsNone(handler.redirect_request(request, None, 302, "Found", {}, "https://evil.test"))

    def test_webhook_raw_hmac_and_exact_shop(self):
        raw = b'{"id":1, "title":"Example"}'
        digest = base64.b64encode(hmac.new(b"synthetic-secret", raw, hashlib.sha256).digest()).decode()
        headers = {"X-Shopify-Hmac-SHA256": digest, "X-Shopify-Shop-Domain": "example.myshopify.com", "X-Shopify-Topic": "products/update"}
        self.assertTrue(connector.verify_shopify_webhook("demo", raw, headers))
        self.assertFalse(connector.verify_shopify_webhook("demo", raw + b" ", headers))
        self.assertFalse(connector.verify_shopify_webhook("other", raw, headers))
        for key, value in [("X-Shopify-Shop-Domain", "other.myshopify.com"), ("X-Shopify-Topic", "unknown/topic"), ("X-Shopify-Hmac-SHA256", "invalid")]:
            self.assertFalse(connector.verify_shopify_webhook("demo", raw, {**headers, key: value}))
        self.assertFalse(connector.verify_shopify_webhook("demo", b"x" * (2 * 1024 * 1024 + 1), headers))
        self.assertFalse(connector.verify_shopify_webhook("demo", raw.decode(), headers))


if __name__ == "__main__":
    unittest.main()
