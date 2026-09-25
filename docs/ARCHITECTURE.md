# Local application architecture

run.py serves first launch onboarding and a local archive from a loopback HTTP server. Configuration contains only nonsecret mode settings. Provider keys stay in memory or come from environment variables. Each page load receives a setup token; API calls must include it. Writes also require the expected Origin and Host.

connectors.py parses video references, enumerates at most two playlist pages, and extracts links from a bounded public HTML response. Website connections resolve and validate addresses, pin the TLS connection to the chosen address, and repeat validation after redirects. This does not execute page scripts or implement a general crawler.

Import jobs receive a stable identity based on source bytes and processing settings. One worker runs at a time. Media duration is checked with ffprobe. The OpenAI path uses whisper-1 to produce timed segments. The local path converts media to 16 kHz mono WAV, runs whisper.cpp with VTT output, and validates the cues. Validated raw documents are saved before indexing. Whitespace normalization creates a separate readable version.

The local mode uses a keyword index without an AI provider. The OpenAI path uses keyword and vector search. The existing retrieval core hashes passages and reuses unchanged vectors in the provider path. A successful complete index is atomically replaced. Documents and the index are separate files, so this is not a transactional database. Resume reconstructs the document collection from saved transcripts. Operate only one process per data directory.

Optional question generation requests JSON and verifies that every proposed answer is an exact excerpt from its referenced cue. All drafts remain marked for human review. This is editorial generation over one transcript, not a conversational RAG answer endpoint.

The UI is static HTML, CSS, and JavaScript with no frontend build step. Imported text uses textContent. The server applies a content security policy, bounded request bodies, socket timeouts, and a small concurrent request limit. Credentials, uploads, and diagnostics are never exported as browser status data. Archive export deliberately includes user content.

Persistent state does not guarantee exactly once provider billing. A process failure between a provider response and local commit can require repeating the call. No automatic transcription or generation retries are performed. Embeddings retain their existing bounded transient retry policy.

The original retrieval core decisions are documented in RETRIEVAL_DEMO.md and evaluated in EVALUATION.md. Those fixture metrics do not measure real transcription, question quality, or deployed application performance.
