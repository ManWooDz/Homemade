---
status: accepted
---

# Account-owned notifications with foreground reconciliation

On 2026-10-15 the user chose account-persisted notifications/read state shared across devices, rather than browser-only history, and foreground in-app delivery rather than closed-app push. This adds durable authenticated notification storage while avoiding a scheduler, push service or extra package; expiry checks run when the app opens/returns, so a closed app does not deliver reminders. Implementation and live migration still require the separate approvals described in the notification plan.
