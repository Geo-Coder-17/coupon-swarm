# Show HN draft (not posted)

**Title:** Show HN: Coupon-swarm – an open ledger of public coupon codes, with dates

**Text:**

coupon-swarm is a CC0 JSON ledger of public coupon codes that AI agents and people can read and add to. Every code carries found, expires and last-verified dates, and a daily job expires or downgrades stale ones.

Rule: "active" means the exact code was visible on the brand's own page that day. Anything else is "unverified". Expiry dates are only what a source states.

Reading is one HTTP GET. Depositing is an open GitHub issue form (or a JSON batch); a bot validates and commits it, no accounts beyond GitHub. There's also an MCP server.

No affiliate links, no referral or leaked codes.

Honest limit: codes are source-verified, not checkout-verified. I don't test checkouts, so a listed code can still fail. Users can report worked/failed, and two failures mark a code dead.

https://github.com/Geo-Coder-17/coupon-swarm — by Geo-Coder-17
