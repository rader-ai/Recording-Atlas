# Content Intelligence Lab

A runnable portfolio reconstruction by Chris Rader, prepared with Codex assistance.

Search a transcript archive, open a timestamped source passage, simulate an embedding outage, and inspect the decisions behind ingestion and retrieval. Every sample transcript was written for this project. No private source code, recordings, credentials, database exports, brand assets, or Git history are included.

## The problem

Long recordings hide useful information. Listeners often remember the idea but not the words a speaker used. Editors need enough source context to verify a passage. The system also has to remain useful when a paid dependency is unavailable.

This sample demonstrates a practical response: preserve timestamps, make indexing incremental, combine retrieval methods, and expose sources directly.

## Run in two minutes

Requires Python 3.11 or newer. The default mode uses only the standard library.

```sh
python3 lab.py index
python3 lab.py serve
```

Open http://127.0.0.1:8765. Search, switch retrieval modes, simulate a vector outage, and open source context.

```sh
python3 -m unittest discover -s tests -v
python3 lab.py plan
python3 lab.py evaluate
python3 lab.py search --query "protect eyes while soldering"
```

## What is implemented

| Capability | Implementation |
| :--- | :--- |
| Transcript ingestion | Validated JSON cues and a local WebVTT importer |
| Chunking | Cue boundary grouping with overlap and retained timestamps |
| Incremental indexing | Content hashes, metadata refresh without new embeddings, full and partial update modes |
| Operational controls | Preflight character budget, bounded batches, bounded provider retries, atomic index replacement |
| Retrieval | BM25 style keyword scoring, cosine vector comparison, parallel retrieval, reciprocal rank fusion |
| Source inspection | Exact excerpts, document deduplication, timestamps, source context dialog |
| Failure handling | Keyword fallback when the vector service fails, bounded query cache, query size limits |
| Review interface | Responsive local browser demo, retrieval controls, explicit fixture disclosure |
| Evaluation | Labeled synthetic development queries, hit rate and reciprocal rank metrics |

## Fixture mode and real model mode

The default uses a transparent concept vector fixture. It groups a few related words and adds small hashed lexical dimensions. It is not a pretrained embedding model and is not evidence of general semantic quality. Its purpose is reproducible inspection without account setup or spending.

The optional adapter sends text to OpenAI's embedding endpoint. Set OPENAI_API_KEY in your shell using your normal secret management process. Do not place it in source files or browser code. Choose a separate index:

```sh
python3 lab.py index --provider openai --index build/openai.json
python3 lab.py serve --provider openai --index build/openai.json
```

These commands make paid provider calls. They were not executed during preparation. The adapter was tested with mocked HTTP responses, including rate limiting, authentication failure, response ordering, and invalid vectors. The index and query provider must match.

API contract: https://developers.openai.com/api/reference/resources/embeddings/methods/create

## Inspect incremental behavior

Run index twice. On the second run, changed is zero and no embeddings are requested. Change only a document title and its vector can be reused while metadata updates. Changing passage text embeds the affected chunks. The tests also cover removal and partial updates.

```sh
python3 lab.py plan --max-input-chars 100000
```

The character limit is enforceable before embedding. The displayed token estimate is only a character based approximation, not a billing guarantee. Provider retries and query calls can add cost. This demo does not claim to enforce an account dollar budget.

## Bring a transcript

```sh
python3 import_vtt.py sample.vtt --id sample --title "Sample workshop"
```

The importer prints one document. Add it to data/transcripts.json and rebuild the index. It accepts ordinary ordered, nonoverlapping cues and strips basic VTT markup. Overlapping speaker captions are deliberately rejected and need preprocessing.

Speech recognition itself is not bundled. The original private work includes transcription; this portable reconstruction starts from a transcript so it can run without a model download, licensed audio, or provider credentials.

## Evidence and limits

This is retrieval with source references, not a generative RAG answer system. Exact excerpt checking confirms that a quotation exists in a passage; it does not evaluate a generated answer's truthfulness.

The included query set is a small authored development set. It shares a domain with the fixture concepts and is not an independent benchmark. Its results must not be used as production accuracy claims. See docs/EVALUATION.md.

The local server binds to loopback, restricts the Host header, and applies a simple in memory rate limit. It is a review server, not a deployable public service. It has no authentication, distributed cache, durable request queue, multi tenant access model, or production monitoring. Queries wait for retrieval tasks to finish; the UI does not stream intermediate results.

## Portfolio context

Chris's private projects connect customer research and content strategy to transcription, retrieval, editorial validation, and application delivery. This project is a new, smaller reconstruction of selected patterns. It should be presented as a portfolio sample created with coding agent assistance, not as a copy of the production system or proof of historical scale.

See docs/CASE_STUDY.md for the product narrative and docs/ARCHITECTURE.md for decisions and tradeoffs. Public release is staged for review. No open source license grant has been added; select an appropriate license before inviting reuse.
