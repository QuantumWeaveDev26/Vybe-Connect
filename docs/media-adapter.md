# WhatsApp Cloud API media adapter

`whatsapp_media.py` is a Python standard-library provider adapter. It performs no
network action on import or when inspecting configuration. The tests replace
the `_open` transport; they never contact Meta or spend provider credits.

## Integration contract

* `media_status(tenant)` returns `configured`, `live`, `max_bytes` and a
  `supported_types` MIME-to-message-kind map. It neither exposes credentials nor
  verifies provider permissions or connectivity.
* `upload_media(tenant, filename, content_type, data)` accepts bytes and returns
  the numeric Meta media ID as a string. It requires server configuration and
  performs exactly one multipart `POST /{PHONE_ID}/media`. An upload is an
  explicit external operation; it works with `LIVE=false` because it does not
  send a message. The authenticated caller must authorize and audit uploads.
* `send_media(tenant, phone, media_id, kind, caption='', filename='')` performs
  one JSON `POST /{PHONE_ID}/messages`, returning Meta's message acceptance ID.
  It requires `LIVE=true`. It accepts `image`, `audio`, `video`, or `document`,
  a numeric uploaded ID, and an international phone string (optional leading
  `+`, removed in the request). Captions are locally limited to 1,024 characters
  and forbidden for audio. Display filenames are document-only.

Both endpoints use `https://graph.facebook.com` and the configured Graph version.
Settings come from the existing `meta.settings(tenant)` workspace environment
(`TW_META_<TENANT>_TOKEN`, `_PHONE_ID`, `_VERSION`, `_LIVE`). Token, numeric phone
ID and version syntax are validated before sending. Credentials remain on the
server. Redirects are disabled; there are no download or arbitrary-URL inputs.

All validation/configuration failures raise the existing `meta.ProviderError`
with `definitive=True`. Provider HTTP 4xx responses are definitive except HTTP
408. Redirects, server errors, connection/timeout failures, malformed JSON and
missing/invalid IDs are uncertain (`definitive=False`). Error messages never
copy provider response text or credentials. There are no automatic retries.
An uncertain result must be reconciled before an operator chooses to retry.

## Supported subset and local limits

All uploads must be nonempty and at most **5 MiB (5,242,880 bytes)**, a conservative
application cap. MIME strings must match exactly:

| MIME | Kind | Filename extensions |
| --- | --- | --- |
| `image/jpeg` | image | `.jpg`, `.jpeg` |
| `image/png` | image | `.png` |
| `audio/ogg` | audio | `.ogg`, `.opus` |
| `audio/mpeg` | audio | `.mp3`, `.mpeg` |
| `video/mp4` | video | `.mp4` |
| `application/pdf` | document | `.pdf` |

Filename validation allows only 1–120 ASCII letters, digits, spaces, dots,
dashes and underscores; the first character must be alphanumeric. Paths, `..`,
quotes, control characters and trailing dots/spaces are rejected. These checks
also protect multipart headers. MIME and basic container signatures must agree;
OGG additionally needs a mono Opus identification header. A random multipart
boundary is checked against file bytes before assembly.

Signature checks are a preliminary format screen, not complete file decoding,
malware detection, image bit-depth checks or MP4 H.264/AAC codec verification.
Meta remains responsible for final format acceptance. There is no transcoding,
media retrieval/download, deletion, expiry handling or storage in this module.

The HTTP/store integration must enforce tenant ownership of uploaded media,
matching stored MIME to the send kind, authenticated permissions, consent,
service-window eligibility, upload limits, audit records and duplicate-send
protection. The adapter alone cannot establish these from a numeric media ID.
Upload success is not message acceptance; acceptance is not delivery. Only
verified provider status webhooks establish delivered/read states.

## Official reference evidence

Reviewed on 2026-10-29, without provider calls:

* [Meta WhatsApp Business: Sending WhatsApp Media Messages From An App](https://whatsappbusiness.com/blog/media-messages-via-app/)
  demonstrates multipart `file`, `type` and `messaging_product` upload fields,
  the phone-ID `/media` route, and ID-based `/messages` schema.
* [Meta's official WhatsApp Cloud API Postman collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api)
  identifies the official Cloud API collection, bearer authentication, and
  messaging permission.
* [Meta-hosted image SDK reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/image/),
  [audio reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/audio/),
  [video reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/video/),
  and [document object reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/types/DocumentMediaObject/)
  establish these media formats and the ID/caption/document-filename pattern.
  These SDK references are explicitly archived; they are bounded schema evidence.
* [Cloud API media reference](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media/)
  is the canonical current reference, but returned HTTP 429 to the documentation
  fetch in this session. Current provider-wide size/codec guarantees were not
  independently established from that page. The module intentionally implements
  only the listed local subset/cap and does not claim complete media parity.

## Verification

Run from the TeamWave directory in PowerShell:

```powershell
python -m unittest discover -s tests -p test_whatsapp_media.py -v
```

Tests cover multipart schema, tenant configuration isolation, LIVE send gate,
all four message kinds, captions/document filenames, unsafe input and MIME
screening, server rejection classification, uncertain transport and malformed
responses, response bounds, redirect refusal and no automatic retries. No live
upload, message delivery, provider permission, codec/device or UI acceptance
verification has been performed.
