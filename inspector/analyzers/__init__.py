"""Tier 1 static analyzers. Each module exposes ``analyze(sample_path, result, ...)``
and mutates the shared :class:`contract.InspectorResult`. None of them execute the
sample; the container's isolation is the safety boundary, not parser correctness.
"""
