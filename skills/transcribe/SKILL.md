---
name: transcribe
description: Transcribe a local audio/video file, or a video at a URL (YouTube etc.), to text using yt-dlp (to fetch remote video/audio) and the MacWhisper CLI (mw). Use when the user wants a transcript of a video URL, a downloaded recording, a webinar, or any local audio/video file.
---

# Transcribe

Turns a video URL or a local audio/video file into a text transcript, using
`yt-dlp` for remote sources and the MacWhisper CLI (`mw`) for the actual
speech-to-text.

## Prerequisites

- `yt-dlp` on PATH (only needed for URL sources). Install with `brew install yt-dlp` if missing.
- MacWhisper CLI (`mw`) installed via MacWhisper -> Settings -> Advanced ->
  Command-Line Tool. Binary lives at `/usr/local/bin/mw`. Verify with `mw`
  (prints app status, active model, and example commands) or `mw version`.
- MacWhisper.app itself must be installed and have at least one model
  downloaded (`mw models list` shows what's available). `mw` talks to the
  running/installed app; it is not a standalone transcription engine.

## Procedure

1. **Get the audio.**
   - Local file already on disk: skip to step 2.
   - Remote video (YouTube or otherwise): download audio-only, it's faster
     than full video and sufficient for transcription:
     ```bash
     yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "<video_url>"
     ```
     `-x` / `--extract-audio` pulls just the audio stream; `--audio-format
     mp3` transcodes it. yt-dlp sanitizes titles into filenames, which can
     leave odd full-width Unicode punctuation (e.g. `：` `｜`) in place of
     `:`/`|`. Rename the output to something shell-safe before the next step:
     ```bash
     mv "<messy yt-dlp filename>.mp3" <slug>.mp3
     ```

2. **Transcribe with `mw`.**
   ```bash
   mw transcribe <file> --no-speakers -o transcript.md --format md
   ```
   - Default output is plain `txt`; for a release-notes-style working doc,
     `--format md` reads better and still allows `--timestamps`.
   - `--no-speakers` is a reasonable default for single-narrator content
     (webinars, presentations). Drop it (or use `--speakers`) for
     multi-person calls/interviews where diarization is useful.
   - `-o <path>` requires the parent directory to already exist and refuses
     to overwrite by default; add `--overwrite` when re-running.
   - A ~65-minute mp3 transcribes in well under a minute on Apple Silicon
     with the default local model (no network calls, no per-minute cost).
   - Full flag reference: `mw help transcribe`.

3. **Commit only the transcript and any derived docs.** Media stays in the
   working directory (gitignored, e.g. `*.mp3`/`*.mp4`/`*.webm`/`*.wav`/`*.m4a`)
   or is deleted once the transcript is captured.

## Key flags (from `mw help transcribe`)

- `--model <engine:model-id>`: override the app's currently selected model for this run.
- `--language <code|auto>`: source language; defaults to the app's setting.
- `--format <txt|srt|vtt|json|csv|md|html|avid>`: output format, default `txt`.
- `--style <transcript|subtitles|segments>`: export style; not all formats support every style.
- `--timestamps` / `--no-timestamps`: per-segment timestamps (text formats only).
- `--speakers` / `--no-speakers`, `--speaker-names` / `--no-speaker-names`: diarization on/off, and whether to label segments with speaker names.
- `-o, --output <path>`: single file output (parent dir must exist); `--output-dir <dir>` for batch/folder input.
- `--overwrite`: required to replace an existing output file.
- `--stream`: print segments live as they finalize (single input only, incompatible with non-txt formats).

## Gotchas

- `mw` is a thin client for the MacWhisper **app**: with the app missing or
  no model downloaded, `mw transcribe` fails. Bare `mw` shows the status.
- yt-dlp filenames can contain full-width Unicode lookalikes for `:` and `|`
  (Windows-filename sanitization); rename before piping into other tools.
- `-o` errors out if the target file already exists; pass `--overwrite` on
  re-runs instead of deleting first.
