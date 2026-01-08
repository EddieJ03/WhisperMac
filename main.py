from helpers import get_blackhole_device_index, request_screen_recording_permission
import threading
import subprocess
from AppKit import NSApplication
from subtitles import SubtitleOverlay
import argparse


def read_whisper(overlay, language_to_translate=None):
    """Read whisper-stream output and update overlay"""
    args = [
        "./whisper.cpp/build/bin/whisper-stream",
        "-m",
        (
            "./whisper.cpp/models/ggml-large-v3-q8_0.bin"
            if language_to_translate
            else "./whisper.cpp/models/ggml-large-v3-turbo.bin"
        ),
        "-t",
        "6",
        "--step",
        "1000",
        "--length",
        "5000",
        "--keep",
        "500",
        "-c",
        str(get_blackhole_device_index()),
        "--subprocess-mode",
        "-svm",
        "./whisper.cpp/models/ggml-silero-v6.2.0.bin",
        "--denoise",
    ]

    if language_to_translate:
        args.append("-tr")
        args.append("-l")
        args.append(language_to_translate)

    proc = subprocess.Popen(
        args=args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    overlay.set_text("Setting up...")

    # give the overlay the reference so it can clean it up
    overlay.whisper_proc = proc

    for line in proc.stdout:
        line = line.strip()
        if line.startswith("<text>:"):
            text = line[len("<text>:") :]
            overlay.set_text(text)
        elif line.startswith("<Ready") or line.startswith("<error>:"):
            overlay.set_text(line)


def main(language_to_translate=None):
    app = NSApplication.sharedApplication()
    request_screen_recording_permission()

    import time

    time.sleep(0.3)

    overlay = SubtitleOverlay.alloc().init()
    overlay.show()

    threading.Thread(
        target=read_whisper, args=(overlay, language_to_translate), daemon=True
    ).start()

    print("Subtitle overlay started!")
    print("Drag the window to reposition. Close terminal to quit.")
    print(
        "If not visible over full-screen: System Settings → Privacy & Security → Screen Recording"
    )

    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-tr",
        "--translate",
        help="input language to translate (NOTE: output translation will always be in English)",
    )
    args = parser.parse_args()
    main(language_to_translate=args.translate)
