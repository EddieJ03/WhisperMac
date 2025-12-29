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
