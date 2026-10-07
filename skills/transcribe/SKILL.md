---
name: transcribe
description: Transcribe a local audio/video file, or a video at a URL (YouTube etc.), to text using yt-dlp (to fetch remote video/audio) and the MacWhisper CLI (mw). Use when the user wants a transcript of a video URL, a downloaded recording, a webinar, or any local audio/video file.
---

# Transcribe

Turns a video URL or a local audio/video file into a text transcript, using
`yt-dlp` for remote sources and the MacWhisper CLI (`mw`) for the
speech-to-text, which runs locally on the app's model.

## Prerequisites

- `yt-dlp` on PATH, for URL sources only. Install with `brew install yt-dlp` if missing.
- MacWhisper CLI (`mw`), installed from MacWhisper -> Settings -> Advanced ->
  Command-Line Tool, at `/usr/local/bin/mw`.
- MacWhisper.app installed with at least one model downloaded (`mw models list`).
  `mw` is a thin client for the app, so `mw transcribe` fails without it; bare
  `mw` prints the app status and active model, and `mw version` the CLI version.

## Procedure

1. **Get the audio.**
   - Local file already on disk: skip to step 2.
   - Remote video (YouTube or otherwise): download audio only, which is faster
     than full video and enough for transcription:
     ```bash
     yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "<video_url>"
     ```
     `-x` / `--extract-audio` pulls just the audio stream; `--audio-format
     mp3` transcodes it. yt-dlp sanitizes titles into filenames with
     full-width Unicode lookalikes (`：` `｜`) for `:` and `|`, so rename the
     output to something shell-safe before the next step:
     ```bash
     mv "<messy yt-dlp filename>.mp3" <slug>.mp3
     ```

2. **Transcribe with `mw`.**
   ```bash
   mw transcribe <file> --no-speakers -o transcript.md --format md
   ```
   - Default output is plain `txt`; `--format md` reads better as a working
     doc and still allows `--timestamps`.
   - `--no-speakers` suits single-narrator content (webinars, presentations).
     Use `--speakers` for multi-person calls and interviews, where diarization helps.
   - `-o <path>` needs its parent directory to exist and refuses to overwrite;
     add `--overwrite` when re-running.
   - Full flag reference: `mw help transcribe`.

3. **Keep the media out of git.** Leave it untracked or delete it once the
   transcript exists; tell the user where the transcript landed.

## Other flags

`--model`, `--language`, `--timestamps`, `--output-dir` (batch or folder input) and `--stream` cover the rest; `mw help transcribe` is the always-current reference.
