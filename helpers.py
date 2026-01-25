import re
import sounddevice as sd
import ScreenCaptureKit


def get_blackhole_device_index():
    """Find the device index for BlackHole audio device."""
    devices = sd.query_devices()
    device_idx = 0
    for _, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            if "blackhole" in device["name"].lower():
                return device_idx
            device_idx += 1
    raise RuntimeError("BlackHole device not found. Is it installed?")


def request_screen_recording_permission():
    """Request screen recording permission using ScreenCaptureKit"""
    print("Requesting screen recording permission...")
    try:
        ScreenCaptureKit.SCShareableContent.getShareableContentWithCompletionHandler_(
            lambda content, error: print(
                f"Permission: {'granted' if content else 'denied'}"
            )
        )
    except Exception as e:
        print(f"ScreenCaptureKit error: {e}")
        print("Grant Screen Recording permission in System Settings")


def text_preprocessing(text: str):
    lines = _add_newlines_after_punctuation(text)
    return "\n".join(_split_long_lines(lines))


def _add_newlines_after_punctuation(text: str, min_length=30):
    """Insert newline after punctuation only if preceding text exceeds min_length"""
    result: list[str] = []
    current_line = []

    parts = re.split(r"([.!?])", text)
    for part in parts:
        if part in ".!?":
            current_line.append(part)
            current_text = "".join(current_line).strip()

            if len(current_text) > min_length:
                result.append(current_text)
                current_line = []
            else:
                current_line.append(" ")
        else:
            current_line.append(part)

    if current_line:
        remaining = "".join(current_line).strip()
        if remaining and any(char.isalnum() for char in remaining):
            if len(result) > 0 and len(result[-1] + " " + remaining) <= min_length:
                result[-1] = result[-1] + " " + remaining
            else:
                result.append(remaining)

    return result


def _split_long_lines(result: list[str], max_length=60):
    """
    Splits strings in the list that exceed max_length
    at the space closest to the middle.
    """
    output: list[str] = []

    for line in result:
        if len(line) <= max_length:
            output.append(line)
            continue

        mid = len(line) // 2
        spaces = [i for i, char in enumerate(line) if char == " "]

        if not spaces:
            output.append(line)
            continue

        split_index = min(spaces, key=lambda x: abs(x - mid))

        part1 = line[:split_index].strip()
        part2 = line[split_index:].strip()
        output.extend([part1, part2])

    return output
