from helpers import get_blackhole_device_index, request_screen_recording_permission
import threading
import subprocess
from AppKit import NSApplication
from subtitles import SubtitleOverlay


def read_whisper(overlay):
    """Read whisper-stream output and update overlay"""
    proc = subprocess.Popen(
        [
            "./whisper.cpp/build/bin/whisper-stream",
            "-m",
            "./whisper.cpp/models/ggml-large-v3-turbo.bin",
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
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    # give the overlay the reference so it can clean it up
    overlay.whisper_proc = proc

    for line in proc.stdout:
        line = line.strip()
        if line.startswith("U:"):

            text = line[2:]
            overlay.set_text(text)


def main():
    app = NSApplication.sharedApplication()
    request_screen_recording_permission()

    import time

    time.sleep(0.3)

    overlay = SubtitleOverlay.alloc().init()
    overlay.show()

    threading.Thread(target=read_whisper, args=(overlay,), daemon=True).start()

    print("Subtitle overlay started!")
    print("Drag the window to reposition. Close terminal to quit.")
    print(
        "If not visible over full-screen: System Settings → Privacy & Security → Screen Recording"
    )

    app.run()


if __name__ == "__main__":
    main()
