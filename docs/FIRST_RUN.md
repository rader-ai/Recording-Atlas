# First run walkthrough

## Try the idea without accounts

Run python3 run.py --open from the project folder. Select Explore the example and click Try the example archive. The server indexes six original sample transcripts. Open the archive and search for a topic. Expand a transcript to inspect its source passages. No paid calls occur in this mode.

## Process your first recording

Start a different data directory if you already loaded the example. Choose Use your own content and enter an OpenAI API key. Save connections. A connection check verifies access but does not prove billing or every model permission.

Paste a video, playlist, or website URL in Add content. Playlist discovery requires a YouTube Data API key. Select a recording from the results to fill its title and source reference. Attach a WebVTT transcript or a recording that you can use. You can also skip discovery and upload directly.

Check the file size and processing explanation. Select question drafts if wanted. Confirm that you approve sending this content to OpenAI for paid processing, then create the import. Click Start processing on the saved job. Progress moves through transcription, archive, indexing, and optional questions.

If a job fails, its card explains the problem. Correct the account or source issue and resume. Finished stages are reused. Timeouts can still incur charges and retries may repeat an uncommitted request.

Open the archive to search, inspect transcripts, review question drafts, and export JSON. Draft answers quote the transcript; the source check does not prove that a generated question is a faithful interpretation. Nothing is automatically published.

## Setup troubleshooting

Python missing: install Python 3.11 or newer from python.org and reopen your terminal. Confirm python3 --version, or py -3 --version on Windows.

Media tools missing: install FFmpeg for your operating system using ffmpeg.org. Ensure ffprobe is on PATH. Confirm ffprobe -version works, then restart the application. WebVTT imports do not require these tools.

Provider access denied: check API credentials, project permissions, billing, and model availability. A ChatGPT subscription does not supply API billing.

Playlist discovery failed: enable YouTube Data API v3 in the key's Google project and check key restrictions and quota. Private playlists and OAuth flows are not supported in this version.

No website videos found: only ordinary links and embeds in the fetched HTML are read. Scripts and linked pages are not processed. Paste a specific video or playlist instead.

Captions missing: upload an exported WebVTT transcript or the source recording. This release does not acquire YouTube captions automatically.

File too large: compress or export a smaller media file, or supply WebVTT. Maximum upload is 20 MB, media duration 90 minutes. Overlapping WebVTT cues need normalization before import.

Provider mode cannot change: start with a different --data-dir. Example vectors are intended only for demonstration transcripts.

Restart requests credentials: browser entered keys intentionally live only in server memory. Reenter them, or supply them through your environment or secret manager.
