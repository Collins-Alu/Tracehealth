# State machines

## Pollution report

```mermaid
stateDiagram-v2
  [*] --> Queued: saved on the phone
  Queued --> PENDING: synced to the server
  Queued --> NeedsAttention: server refused (reason shown)
  NeedsAttention --> Queued: reporter retries
  PENDING --> VERIFIED: verifier confirms
  PENDING --> REJECTED: verifier rejects (reason)
  PENDING --> FLAGGED: verifier flags (reason)
  FLAGGED --> VERIFIED: a different verifier confirms
  FLAGGED --> REJECTED: a different verifier rejects
  VERIFIED --> [*]
  REJECTED --> [*]
```

Queued and NeedsAttention exist only on the phone. VERIFIED and REJECTED are
final (database trigger). Only VERIFIED reports appear on the dashboard, get
health linkages and earn a reward.

## Payout

```mermaid
stateDiagram-v2
  [*] --> PENDING: report VERIFIED and reporter consented
  PENDING --> SUCCESS: provider confirms payment
  PENDING --> PENDING: temporary error, retried with backoff
  PENDING --> FAILED: refused, attempts used up, no result in 24 h, or outcome unknown
  FAILED --> PENDING: administrator retries (after checking)
  SUCCESS --> [*]
```
