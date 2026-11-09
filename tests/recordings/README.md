# HTTP fixtures

Ordinary tests block sockets and use HTTPX transport injection. Each replay exchange
matches method, full URL, and SHA-256 of request bytes, and fails on an unmatched request.

Synthetic OAuth and inference-failure fixtures are labelled synthetic. Successful model
responses used in unit tests are deliberately synthetic component inputs, not recorded
system acceptance. The 16 baseline actual-provider inference recordings support offline
system tests and belong in Git. Missing recordings fail their system tests with the case
name and expected path. Replay does not establish current live model quality; that is
checked separately through live evaluation and owner review.

When capturing actual inference, retain only request-body hashes and sanitized SSE bodies;
exclude Authorization headers, OAuth codes/callbacks, identity tokens, refresh/access tokens,
and personal account details. Record model, prompt/schema/input revisions and provenance.
Never copy model output into approved golden expectations.


Personalized successes require actual work/fit/optional-exception streams captured by the same
full-suite live run after source/expectation review. `test_personalized_cli.py` consumes two or
three ordered exchanges by request-byte hash and fails explicitly when a cassette is missing.
It never substitutes synthetic successes or permits unrecorded sockets. The synthetic prefixes
in `test_personalized_failures.py` exist solely to reach later-stage failure boundaries; they do
not establish successful CLI acceptance. The 64 current actual-provider cassettes passed the full live/replay suite and bound owner review. The shared manifest and owner review cover legacy and personalized results.

Superseded untracked development streams are archived in ignored `.local/evaluations/`; the versioned inference directory retains every request hash needed by the current full suite.
