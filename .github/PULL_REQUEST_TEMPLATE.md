## What this PR adds or changes

- [ ] New codes (list ids: `store:CODE`)
- [ ] Updated expiry / verification dates
- [ ] Status changes (expired / dead)

## Checklist

- [ ] Every code is a public promotional code (no referral, single-use, leaked or guessed codes)
- [ ] Every entry has `found_on`, a `source_url`, and `expires_on` if the source states one
- [ ] `status` is `active` only where `last_verified` is set
- [ ] `python scripts/validate.py` passes locally

Submitted by (model id / handle):
