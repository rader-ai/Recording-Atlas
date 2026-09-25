# Local Whisper on a Mac

Recording Atlas can transcribe an uploaded recording with `whisper.cpp` on your Mac. In this mode the recording, transcript, and search queries stay in the local application. Search uses keywords. It does not provide semantic vector search or generated question drafts.

## Set up once

1. Install Python 3.11 or newer. If you have Homebrew, install the two media tools with:

```sh
brew install ffmpeg whisper.cpp
```

Homebrew provides `ffmpeg`, `ffprobe`, and `whisper-cli`. Confirm `python3 --version`, `ffprobe -version`, and `whisper-cli --help` work in Terminal. You can also [build whisper.cpp from source](https://github.com/ggml-org/whisper.cpp) instead of using Homebrew.

2. Download a compatible `ggml` model using [the project's model instructions](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md). Start with an English model for English recordings, such as `ggml-base.en.bin`. Larger models need more memory, disk space, and processing time. The Homebrew package does not include the model.
3. Set `WHISPER_MODEL_PATH` to the model file's full path. If `whisper-cli` is not on PATH, set `WHISPER_CLI_PATH` to its executable path.
4. Launch Recording Atlas with a new workspace. Environment variables must be set in the same Terminal session that starts the app:

```sh
export WHISPER_MODEL_PATH="/absolute/path/to/ggml-base.en.bin"
export WHISPER_CLI_PATH="/absolute/path/to/whisper-cli"
python3 run.py --data-dir ./build/local-archive --open
```

If `whisper-cli` is already on PATH, `WHISPER_CLI_PATH` is optional. The app's setup screen checks the tools and model. Choose **Use Whisper on this Mac** and **Save setup**. Upload a recording or WebVTT transcript that you can use. A timed WebVTT upload does not need `whisper-cli`.

A copied video or playlist link is only a source reference. The app cannot fetch YouTube audio or captions from that link. Upload the media or transcript separately.

## What happens during import

The app checks duration with `ffprobe`, converts the input to a temporary 16 kHz mono WAV using FFmpeg, runs `whisper-cli` with VTT output, validates the timed cues, saves the raw transcript, and creates a readable archive. Temporary WAV and output files are removed when the command finishes or fails. The import limit is 50 MB and 90 minutes. A long recording can require several hundred MB of free temporary storage and substantial processing time. No specific Mac performance is promised.

The archive creates a local keyword index. Search will find words present in the transcript, including inflected and related words only where their literal terms overlap. It will not infer meaning the way a trained embedding model might. This is an intentional local mode tradeoff.

No OpenAI key is required for local transcription and keyword search. YouTube playlist discovery, if you choose it, uses the YouTube Data API and your Google key. Public website discovery fetches the entered page. Those optional discovery requests are separate from local processing.

## Troubleshooting

**Command missing:** Confirm `WHISPER_CLI_PATH` points to an executable or that `whisper-cli` is on PATH. Restart the app after changing environment variables.

**Model missing:** Set `WHISPER_MODEL_PATH` to an existing compatible `ggml` file. The app does not download models automatically.

**Audio fails:** Confirm FFmpeg can read the file and that your model fits in available memory. The app checks for a VTT output even if the command reports success.

**Need meaning based search or draft questions:** Start a separate data directory in OpenAI mode. That mode sends selected content and queries to the provider and can incur charges. A local archive cannot change processing mode after documents are imported.

The local adapter is exercised with mocked command runs and WebVTT validation. It has not been run on a Mac in this repository's verification environment. See [whisper.cpp CLI options](https://github.com/ggml-org/whisper.cpp/blob/master/examples/cli/README.md) for upstream details.
