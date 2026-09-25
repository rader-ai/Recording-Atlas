# A guided tour of Recording Atlas

Recording Atlas is a public reconstruction of part of a larger church content project. The original problem was practical: years of recorded teaching existed, but a listener could not easily find a topic or inspect the exact moment it was discussed. This project shows the product decisions and technical systems that connect source discovery to a searchable archive.

## 1. Discovery precedes processing

Open [connectors.py](../connectors.py) and look at `discover`, `video_id`, and `website_sources`.

A video URL becomes a canonical recording reference. A playlist can be enumerated in bounded pages. A public HTTPS page can yield embedded or linked YouTube videos. The user selects a source before any paid transcription begins. Discovery cannot magically grant access to YouTube captions or media, so the actual import asks for a transcript or recording the user can provide.

The website path has a narrower security boundary than a general web crawler. It accepts public HTTPS destinations, validates resolved addresses, pins the connection to one validated address, checks redirects again, and limits response size. It reads one page and never executes its scripts. See `test_private_destinations_blocked` and `test_playlist_pagination_dedup` in [the onboarding tests](../tests/test_onboarding.py).

## 2. One successful recording is the onboarding milestone

Open [run.py](../run.py), then follow `Workspace.configure`, `create`, `start`, and `process`. The interface in [web/onboarding.html](../web/onboarding.html) offers an example path with no accounts and a real content path with only the needed connections.

The imported file and processing settings produce a stable job identity. The worker saves raw transcript output before building the index. If a later stage fails, the job retains its stage and the user can resume. Repeated imports with unchanged settings find the same job.

This is a deliberate recovery design, with a specific limit: if a provider returned successfully but the process stopped before saving the result, repeating that call may incur another charge. The app never promises exactly once billing.

## 3. Timestamps make retrieval useful

For media input, `transcribe` in [connectors.py](../connectors.py) requests timed segments. For an existing WebVTT transcript, [import_vtt.py](../import_vtt.py) validates ordered cues. `chunk_document` in [core.py](../core.py) groups cues into overlapping passages while retaining source start and end times.

The archive stores raw and readable transcripts separately. The current readable cleanup only normalizes spacing; it does not use a model to silently rewrite the speaker. A search hit includes the passage and timestamp so someone can inspect the context.

## 4. The index does less work on the second run

Follow `Indexer.build` in [core.py](../core.py). It hashes passage content, compares each record with the previous index, and asks the embedding provider only for changed passages. It checks an input character budget before provider calls, processes bounded batches, and atomically replaces a finished index. The tests cover content edits, metadata changes, partial updates, provider failure, and the no change path.

This protects the previous index from an incomplete build. It does not make the separate archive and index files into a transactional database. The app is intended for one local writer.

## 5. Search has two paths and an inspectable result

`Search.query` in [core.py](../core.py) runs keyword and vector search concurrently, combines their rankings, and returns the strongest passage per document. If the vector provider fails, the query can still return keyword results. `validate_excerpt` checks whether quoted text exists in the passage.

The example uses a transparent concept vector fixture to demonstrate the flow without credentials. It is not a pretrained model. The authored query set in [data/queries.json](../data/queries.json) is useful for development but is not an independent quality benchmark. The real content path uses the configured embedding provider.

## 6. Question drafts have a source check and a human checkpoint

`questions` and `validate_questions` in [connectors.py](../connectors.py) ask for proposed questions with an exact quotation and cue index. The validator rejects a draft when the quotation is missing from its cited cue. Accepted drafts keep their timestamps and remain marked for human review.

This check can detect unsupported quotation text. It cannot determine whether the question correctly represents the speaker, whether a passage needs more context, or whether the teaching is accurate. No generated draft is automatically published.

## Run the evidence

```sh
python3 -m unittest discover -s tests -v
node --check web/onboarding.js
```

The repository also has a GitHub workflow for a clean checkout on Python 3.11 and 3.12. The tests use mocks for paid APIs. A live authorized recording import is still needed before claiming the paid path works end to end.

For the product story, read [the case study](CASE_STUDY.md). For a new user, start with [the first run guide](FIRST_RUN.md).
