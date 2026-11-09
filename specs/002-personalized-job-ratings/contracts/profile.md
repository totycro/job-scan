# Profile File Contract

## File and root

One explicitly selected UTF-8 TOML file, optionally UTF-8 BOM decoded before parsing, regular/readable, 1–65,536 bytes. Reject larger files without truncation. Hash original bytes for local provenance and evaluation. The profile is read once and never rewritten. Relative paths resolve from the invocation directory. No home-directory discovery, includes, environment interpolation, remote references, or merging.

Root keys: required integer `schema_version = 1` and required `dimensions` table. Version 1 requires exactly `role_fit`, `technology_fit`, `field_interest`, and `company_affinity`. Unknown fields/dimensions and future versions fail clearly; this is the currently supported profile schema, not a permanent limit on product dimensions. Work arrangement remains an existing qualitative dimension outside this profile version.

## Dimension table

- `importance`: required strict integer 0–5; 0 disables evaluation and numeric contribution. At least one dimension must be enabled. Booleans, floats, numeric strings, negative/out-of-range values fail.
- `preferences`: free-text string; required and nonblank when enabled; may be absent or empty when disabled. Preserve supplied text when building requests.
- `exceptions`: optional array of tables, default empty. Each table has exactly `id`, `kind`, and `preference_quote`.

Describe role responsibilities/seniority/career direction; technologies known versus desired/avoided and willingness to learn; fields of interest; and employer-specific preferences respectively. Profile assertions about an employer are user beliefs/preferences, not verified company facts.

## Exceptional declarations

Each declaration has a unique profile-wide ID matching `[a-z][a-z0-9_-]{0,63}`; `kind` is `compelling_attraction` or `deal_breaker`; `preference_quote` must be nonblank and exactly match a contiguous excerpt of its dimension's preference text. The excerpt states the user's condition in ordinary language. This explicit reference makes exceptional status separate from underlying preference content. Do not add duplicate declarations for the same kind/excerpt in a dimension. Opposite kinds are allowed and can yield a visible conflict.

A declaration adds no numeric bonus/penalty. The excerpt still informs ordinary fit through the unchanged prose. Explicit matching affects only the separate decisive outcome. Do not infer exceptional status merely from strong words in undeclared prose. Validate declarations in disabled dimensions but do not send/evaluate them. An enabled dimension with importance 1 can still contain a decisive exception.

## Diagnostics and starter

TOML duplicate keys/tables fail parsing; unknown keys and cross-field failures fail validation. Report file identity and safe field path/reason, with parser line/column when available. Do not print rejected values, whole documents, or Pydantic input dumps. All profile errors occur before authentication/network effects.

The implementation will ship `examples/preferences.toml` with all four importance values 0, empty text, and comments explaining how to fill them in. It is intentionally incomplete: fill real preferences and enable at least one dimension before assessment. Include examples of optional exceptions, knowledge versus learning interests, disabled semantics, and the fact that relevant profile text goes to the assessment model. A completed fictional profile illustrating this contract is [profile.example.toml](profile.example.toml).
