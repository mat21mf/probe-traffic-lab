# 0001 - Port boundary after map-matching

**Status:** accepted

**Context.** The workflow is to prototype in Python and implement in a typed production language. Porting everything would double the scope, and map-matching is the most research-heavy, most frequently changed part.

**Decision.** The Java core starts at matched traversals (probe_id, segment_id, entry_s, exit_s). It owns speed aggregation and closure detection. Map-matching stays in Python for now.

**Consequences.** The contract is small and stable. Parity is cheap to verify, both on a golden fixture and on a full simulated day in CI. Porting the matcher later would reuse the same contract on its output side.
