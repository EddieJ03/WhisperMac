from helpers import (
    text_preprocessing,
    get_blackhole_device_index,
    request_screen_recording_permission,
)
import threading
import subprocess
from AppKit import NSApplication
from subtitles import SubtitleOverlay
import argparse

prev_line = ""
curr_text = ""


def read_whisper(overlay, language_to_translate=None):
    """Read whisper-stream output and update overlay"""
    args = [
        "./whisper.cpp/build/bin/whisper-stream",
        "-m",
        "./whisper.cpp/models/ggml-large-v3-q8_0.bin",
        "-t",
        "6",
        "--step",
        "800",
        "--length",
        "4000",
        "--keep",
        "500",
        "-c",
        str(get_blackhole_device_index()),
        "--subprocess-mode",
        "-svm",
        "./whisper.cpp/models/ggml-silero-v6.2.0.bin",
        "--denoise",
        "-kc",
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

    global prev_line
    global curr_text

    next_ctr = 0

    for line in proc.stdout:
        line = line.strip()
        if line.startswith("<text>:"):
            curr_text = line[len("<text>:") :]
            overlay.set_text_with_previous(prev_line, text_preprocessing(curr_text))
            next_ctr = 0
        elif line.startswith("<Ready") or line.startswith("<error>:"):
            overlay.set_text(line)
            next_ctr = 0
        elif line.startswith("<next>:"):
            next_ctr += 1
            if next_ctr == 1:
                prev_line = curr_text
                curr_text = ""
            elif next_ctr == 3:  # more silence, update subtitles shown
                overlay.set_text_with_previous(prev_line, curr_text)
            elif next_ctr == 5:  # even more silence, clear everything
                prev_line = ""
                overlay.set_text_with_previous(prev_line, curr_text)


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
