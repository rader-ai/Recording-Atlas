# Recording Atlas

A local content archive application by Chris Rader, reconstructed with coding agent assistance from patterns in his private church projects.

**Turn recorded talks into searchable transcripts and source linked question drafts.**

[First run guide](docs/FIRST_RUN.md) · [Product case study](docs/CASE_STUDY.md) · [Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md)

## Why this exists

Years of recorded teaching can be difficult to find or reuse. Chris built a pipeline to recover that value: transcribe recordings, preserve their context, create a text archive, and make relevant passages easier to discover. This public reconstruction lets another person try those ideas with their own content.

The application opens with guided setup. It explains accounts, checks the computer, accepts source references and uploads, processes a recording, and provides searchable passages and draft questions with source excerpts.

## Start

Requires Python 3.11 or newer and a browser. No Python packages need installation.

```sh
git clone https://github.com/rader-ai/Recording-Atlas.git
cd Recording-Atlas
python3 run.py --open
```

On Windows, use `py -3 run.py --open` if Python is installed through the Windows launcher. Open the exact local address printed in the terminal. The default is http://127.0.0.1:8765.

Choose **Explore the example**, then **Try the example archive**. No accounts, model downloads, or paid calls are needed. Sample transcripts were written for this project and use demonstration vectors, not a trained semantic model.

For your own content, start a separate workspace so real and example indexes remain distinct:

```sh
python3 run.py --data-dir ./build/my-archive --open
```

Choose **Use your own content**, connect an OpenAI API key, and import one transcript or recording. Processing mode cannot change after an archive contains documents. API calls use your account and can incur charges. Search queries also incur embedding usage.

## Requirements and accounts

| Capability | Requirements |
| :--- | :--- |
| Example archive | Python 3.11+, browser, writable storage; no accounts |
| Your own WebVTT transcript | OpenAI API key with billing and embedding model access |
| Audio or video transcription | The above plus FFmpeg with ffprobe on PATH and access to whisper-1 |
| Draft questions | OpenAI access to the text model, default gpt-4.1-mini |
| Playlist discovery | Google project with YouTube Data API v3 enabled and an API key |
| Single YouTube reference or website discovery | No Google key; network access for website discovery |
| Hosting or database | Not required; this version runs locally and stores JSON on disk |

The interface includes links to Python, FFmpeg, API key setup, and Google Cloud. Configure accounts only for the features you need. Keys entered in the browser go to the local server and stay in server memory. They are never written to application files or returned by status endpoints. They must be reentered after restart. Alternatively provide OPENAI_API_KEY and YOUTUBE_API_KEY through your shell or secret manager. Never commit them. This application does not read .env files.

An optional CIL_TEXT_MODEL environment variable selects another compatible JSON capable Chat Completions model. Model access and billing are only proven by a successful real operation. The connection check validates access without running a paid model test.

## What works in this version

1. First launch setup with runtime, storage, and media tool checks.
2. Example archive requiring no accounts.
3. Video reference parsing, playlist discovery up to 100 entries, and YouTube link discovery from one public HTTPS page, up to 50 videos.
4. Uploaded WebVTT transcripts or MP3, M4A, WAV, MP4, and WebM media up to 20 MB. Audio duration is checked before transcription and must be 90 minutes or less.
5. Timestamped cloud transcription, raw transcript preservation, spacing cleanup, incremental embeddings, and combined keyword and vector retrieval.
6. Optional questions answered with exact source excerpts. The application verifies the excerpt exists at the cited cue. Human review is still required.
7. Resumable jobs, source archive inspection, connection replacement, session key clearing, and JSON export.

Paste a link, select a discovered recording, and attach its transcript or media. Link discovery does not automatically download YouTube media or captions. Official caption downloads require additional authorization and video permissions. OAuth connection and caption acquisition are not implemented. Website discovery does not run JavaScript or crawl additional pages.

Question drafts are limited to 60,000 transcript characters. Each indexing operation accepts at most 300,000 changed input characters. These are processing limits, not guaranteed dollar caps. Duration and dollar cost are not known from a selected file in the browser; the UI says so explicitly. Compress large media or provide an exported WebVTT transcript.

## Recovery and data

State lives outside the repository by default, under ~/.local/share/content-intelligence-lab. A supplied --data-dir changes that location. The program restricts new file permissions where the operating system supports it. It does not encrypt the archive at rest.

Raw transcripts and readable normalized transcripts are stored separately. There is no automated rewriting or correction of the speaker's teaching. Completed transcription and index outputs are reused when an import resumes. A crash before a stage is committed can repeat that stage, including paid calls. Interrupted or timed out provider calls may still be billed.

Question generation failure leaves the transcript and search archive available. Resume after resolving the error. Already completed imports are identified by their content and settings to avoid accidental repeats.

Only run one application process per data directory. Stop the application before backing up or deleting that directory. Export JSON includes readable transcripts and question drafts; a full directory backup also preserves uploads, raw transcripts, index, and job state. Keep backups private.

## Validation and limitations

42 automated tests pass on Python 3.12 on Linux. An HTTP smoke test covers setup, example import, archive, search, static assets, and rejection of requests missing the setup token. JavaScript passes Node syntax checking.

Provider behavior, transcript import, failure recovery, source validation, and playlist pagination have mocked test coverage. No paid provider calls or live YouTube account integrations were executed during preparation. Windows and macOS behavior, browser visual layout, and large media performance have not been verified. No universal RAM or speed guarantee is claimed. Cloud processing does not require a GPU; the implementation buffers uploaded media, so it is intended for small local imports.

This is a single user local application, not a hosted service. It binds only to 127.0.0.1, checks Host and Origin, requires a setup token, and restricts website fetches to validated public HTTPS destinations. It has no hosted user accounts, OAuth, local speech model setup, production queue, multi tenant isolation, or publication workflow. Do not expose it through a public tunnel.

No private recordings, credentials, database exports, source code, or repository history are included. This repository is a portfolio reconstruction. No open source license grant is included; contact the author about broader reuse.

## Development

```sh
python3 -m unittest discover -s tests -v
node --check web/onboarding.js
```

The earlier retrieval demo remains available through lab.py. Its original instructions are in docs/RETRIEVAL_DEMO.md. See docs/FIRST_RUN.md for the onboarding walkthrough and docs/CASE_STUDY.md for the product narrative.
