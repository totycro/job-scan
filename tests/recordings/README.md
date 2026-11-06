# HTTP fixtures

Ordinary tests block sockets and use HTTPX transport injection. Each replay exchange
matches method, full URL, and SHA-256 of request bytes, and fails on an unmatched request.

Synthetic OAuth and inference-failure fixtures are labelled synthetic. Successful model
responses used in unit tests are deliberately synthetic component inputs, not recorded
system acceptance. The 16 current actual-provider inference recordings support offline
system tests and belong in Git. Missing recordings fail their system tests with the case
name and expected path. Replay does not establish current live model quality; that is
checked separately through live evaluation and owner review.

When capturing actual inference, retain only request-body hashes and sanitized SSE bodies;
exclude Authorization headers, OAuth codes/callbacks, identity tokens, refresh/access tokens,
and personal account details. Record model, prompt/schema/input revisions and provenance.
Never copy model output into approved golden expectations.
