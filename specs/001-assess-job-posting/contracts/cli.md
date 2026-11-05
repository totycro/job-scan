# CLI Contract: Assess a Job Posting

**Status**: Proposed interface for plan review. Commands below are not implemented yet.

## Assessment

```text
job-scan assess POSTING.html [--source-url URL] [--model MODEL]
```

- Exactly one local UTF-8 HTML file, at most 256 KiB. Reject missing, unreadable, empty, oversized, or undecodable input before model inference.
- `--source-url` accepts HTTP(S) provenance and is never fetched. No linked assets, scripts, or websites are accessed.
- Model defaults to `gpt-6.1-sol` with low reasoning; an unavailable model fails rather than changing models or billing paths.
- Use a signed-in ChatGPT account with granted plan permission. HTML is sent to the configured ChatGPT subscription transport. No API-key fallback exists.
- Buffer the assessment until the stream completes and the result passes schema/evidence validation. Inference has a 180-second total deadline and no automatic retry.

Successful stdout contains source identity, work arrangement and conditions, hybrid home-working details where relevant, evidence with local source locations, fit judgments, and missing/conflicting information. Source quotations may contain HTML; the explanation is plain readable text. No numeric score or overall apply/reject recommendation.

Failures print a concise diagnostic to stderr, without a success report or tokens/raw provider error bodies. Preserve a safe HTTP status/code when useful. Missing work-arrangement details alone are a successful assessment with uncertainty.

| Exit | Meaning |
| --- | --- |
| 0 | Valid assessment, including explicit uncertainty; or successful auth/help operation |
| 1 | Unusable/ambiguous posting, sign-in/permission/usage-limit problem, failed inference, or invalid response/evidence |
| 2 | Invalid CLI arguments or missing/unreadable/invalid/oversized input file |
| 130 | Interrupted by user |

## ChatGPT authentication

```text
job-scan auth login [--account REGISTRATION_ID]
job-scan auth status
job-scan auth use REGISTRATION_ID
job-scan auth logout
job-scan models
```

Login presents “Continue with ChatGPT”, starts a loopback callback, and waits up to 15 minutes for browser authorization. An explicit returning registration reuses its issued client ID; new registration uses job-scan's own app name and host identity. Verify identity and granted plan scope before allowing inference.

Status lists saved registration labels and the active account without secrets and without refreshing tokens. Use selects an existing registration. Logout clears active credentials and attempts revocation, reporting if remote revocation cannot be confirmed. Keep registration identity for reauthorization. Models lists account-available choices through the authorized catalog; it does not select a different model automatically.

Store credentials under `$XDG_CONFIG_HOME/job-scan/`, falling back to `~/.config/job-scan/`, with owner-only directory/file permissions. Do not use the sibling application's credentials. Job-site authentication is outside this feature.

## Provider operation (internal boundary)

`assess_html` receives the HTML, work-arrangement instructions, and JSON schema. It returns a validated response or a typed failure. The real adapter uses OAuth, public Responses, `store=false`, `stream=true`, and completion-gated SSE. Subscription failures stop inference without a paid fallback, as required by the owner's provider constraint. [Official inference contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)

Only tests substitute HTTP transport responses; production has no replay flag. Optional model selection concerns the provider, not runtime configuration of job criteria.
