# Draft assessment examples

These are genericized, curated HTML excerpts derived from owner-supplied pages. They are **not full-page snapshots** and are **not yet an approved golden dataset**. Originals stay outside the repository in the sibling `job-scan-examples` directory.

| Case | Source | Owner's note | Important detail |
| --- | --- | --- | --- |
| [posting-01](posting-01/posting.html) | `posting-01.html` | Hybrid with an unspecified number of days | Home working is possible, but days and mandatory office attendance are unstated |
| [posting-02](posting-02/posting.html) | Newly downloaded `posting-02-embedded.html` | Fully remote | Europe/UK eligibility and time-zone conditions, optional office, and annual office-week invitations remain |
| [posting-03](posting-03/posting.html) | `posting-03.html` | Onsite only | Target role says on-site; related-job cards contain hybrid labels |

Each directory preserves the owner's original short note in `owner-note.txt`. `expected.json` records that note alongside **agent-proposed** detailed findings, evidence, and prohibited conclusions. Its review status stays `pending_owner_review`; none of the detailed checks should be represented as human-approved expectations yet. The draft expectation format can be refined during plan review.

## What changed

- Selected the relevant original DOM subtrees: the job description for case 01, the embedded posting's header/description for case 02, and the main region including related-job cards for case 03.
- Preserved the nesting of retained headings, paragraphs, lists, emphasis, definition terms/values, and related-job cards. Case 03 retains the `Workplace type` term with its `onsite` value and separate hybrid cards.
- Replaced company/person/contact/location identifiers and unrelated prose with generic data. Site-specific IDs/classes are replaced consistently; relationship attributes still refer to the corresponding generic IDs.
- Removed scripts, hidden application/configuration data outside the selected subtrees, media, external links/resources, and application forms. These files test assessment of retained structure and conditions, not browser rendering or handling of whole-site clutter.
- Retained geographic restrictions where they determine remote-work eligibility. Case 02's working conditions are paraphrased into generic wording while preserving their meaning; it does not imply worldwide eligibility or mandatory weekly office attendance.

## Capture finding: case 02

The original `posting-02.html` is the outer careers page. It contains an iframe referring to the actual posting, not the posting's text. Downloading the iframe document directly recovered the remote-role content without executing JavaScript. A separate original snapshot, `posting-02-embedded.html`, was saved outside the repository; the owner-supplied files were not overwritten. Capture methods for cases 01 and 03 were not supplied and must not be assumed.

## Limits and remaining work

Original sizes: case 01 = 83,157 bytes; outer case 02 = 432,757 bytes; recovered embedded case 02 = 73,717 bytes; case 03 = 2,144,770 bytes. The reduced fixtures fit the draft 256 KiB limit. That does **not** establish that the limit supports ordinary full-page inputs: the original case 03 would be rejected, so the limit remains a planning decision for owner review.

The three cases do not cover the entire specification. A stated hybrid allowance/expectation, explicit conflict/missing-arrangement examples, unusable input, and the structure-sensitive pair with unchanged words still need manually authored expectations and owner review. Do not manufacture those expectations from model output or mark validation complete.

Next: owner reviews the generic copies and proposed expectations; resolve the size limit and remaining golden cases before adopting the technical plan. No model assessment or live subscription request has run.
