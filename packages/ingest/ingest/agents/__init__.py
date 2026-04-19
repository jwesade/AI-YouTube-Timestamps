"""Agent-backed steps in the pipeline.

- `normalizer`: merges a cluster of source records into one canonical court.
- (future) `research`: multi-step Claude Agent SDK agent that enriches courts by
  visiting their websites, reading PDFs, and returning structured notes.
- (future) `quality_audit`: samples DB records and verifies them against live data.
"""
