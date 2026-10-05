# 0002 - Dependency-free Java core with a CSV contract

**Status:** accepted

**Context.** The core needs to read the traversal contract and be testable in CI and in restricted build environments.

**Decision.** Plain Java 21 (records, no frameworks), CSV for the contract files, and a self-contained golden test runnable with `java`. Python writes Parquet for its own artifacts, and exports CSV only at the contract boundary.

**Consequences.** It builds with `javac` alone, so no Maven or Gradle is required. Parquet input and JUnit can be added later without changing the contract semantics. The CSV uses round-trip precision (%.17g) so parity can be checked at 1e-9.
