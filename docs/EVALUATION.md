# Evaluation record

27 automated tests passed locally. They cover indexing changes, update scope, budget preflight, source references, query caching, provider response handling, provider failures, and VTT validation. Provider tests use mocked HTTP responses. No paid model calls were made.

The authored development set contains 12 queries against six original transcripts. Keyword retrieval placed the expected source first for 11 queries and within the top three for all 12. Fixture vector and hybrid retrieval placed it first for all 12. These figures are reproducible with `python3 lab.py evaluate`.

These are development checks, not general accuracy estimates. The fixture vocabulary and queries share domain assumptions. The dataset is small, synthetic, and not held out. A serious evaluation needs independently labeled natural queries, relevant passages rather than only document IDs, difficult negatives, and comparison with a real embedding provider.

No original private corpus, production traffic, speech recognition accuracy, or native application was evaluated. A learned embedding provider can produce different results. The browser layout has responsive styles but still requires a visual browser review before publication.
