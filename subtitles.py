"""
Real-time subtitle overlay that appears over full-screen apps on macOS.

You MUST grant Screen Recording permission in:
System Settings → Privacy & Security → Screen Recording

THIS FILE WAS IMPLEMENTED WITH ASSISTANCE FROM CLAUDE OPUS 4.5
"""

import subprocess
import objc
from Foundation import NSObject, NSString
from AppKit import (
    NSApp,
    NSPanel,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSTextField,
    NSButton,
    NSMakeRect,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSBackingStoreBuffered,
    NSTextAlignmentCenter,
    NSLineBreakByWordWrapping,
    NSBezelStyleCircular,
)
import Quartz


class SubtitleOverlay(NSObject):
    # Fixed width, dynamic height for text wrapping
    FIXED_WIDTH = 900
    MIN_HEIGHT = 70
    MAX_HEIGHT = 200
    H_PADDING = 60  # 15px left + 25px button + 20px spacing
    V_PADDING = 30  # 15px top + 15px bottom

    def init(self):
        self = objc.super(SubtitleOverlay, self).init()
        if self is None:
            return None
        self.whisper_proc = None  # Reference to whisper subprocess for cleanup

        # Create panel at bottom center of screen
        frame = NSMakeRect(100, 50, self.FIXED_WIDTH, self.MIN_HEIGHT)

        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel

        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )

        # Critical settings for full-screen overlay
        self.panel.setLevel_(Quartz.CGShieldingWindowLevel())
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setCanBecomeVisibleWithoutLogin_(True)
        self.panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )

        # Semi-transparent dark background
        self.panel.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.1, 0.1, 0.85)
        )
        self.panel.setOpaque_(False)
        self.panel.setHasShadow_(True)

        # Allow dragging by background
        self.panel.setMovableByWindowBackground_(True)

        # Create subtitle label
        content_view = self.panel.contentView()
        label_width = self.FIXED_WIDTH - self.H_PADDING
        self.label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 15, label_width, 40)
        )
        self.label.setStringValue_("Listening...")
        self.label.setTextColor_(NSColor.whiteColor())
        self.label.setFont_(NSFont.systemFontOfSize_weight_(24, 0.5))
        self.label.setBezeled_(False)
        self.label.setDrawsBackground_(False)
        self.label.setEditable_(False)
        self.label.setSelectable_(False)
        self.label.setAlignment_(NSTextAlignmentCenter)
        self.label.setLineBreakMode_(NSLineBreakByWordWrapping)
        content_view.addSubview_(self.label)

        # Create close button (X) in top-right corner
        self.close_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(self.FIXED_WIDTH - 35, self.MIN_HEIGHT - 35, 25, 25)
        )
        self.close_button.setTitle_("✕")
        self.close_button.setBezelStyle_(NSBezelStyleCircular)
        self.close_button.setFont_(NSFont.systemFontOfSize_(14))
        self.close_button.setTarget_(self)
        self.close_button.setAction_(objc.selector(self.closeApp_, signature=b"v@:@"))
        content_view.addSubview_(self.close_button)

        return self

    def closeApp_(self, sender):
        """Close the application when X button is clicked"""
        # Terminate the whisper subprocess if running
        if self.whisper_proc is not None:
            self.whisper_proc.terminate()
            try:
                self.whisper_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.whisper_proc.kill()
        NSApp.terminate_(None)

    def setText_(self, text):
        """Called on main thread - update UI directly"""
        self.label.setStringValue_(text)
        self._resize_for_text(text)

    def set_text(self, text):
        """Thread-safe: schedules UI update on main thread (no lock needed)"""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(self.setText_, signature=b"v@:@"),
            text,
            False,  # Don't block the calling thread
        )

    def _resize_for_text(self, text):
        """Resize window height to fit wrapped text content"""
        # Calculate required height for the text at fixed width
        font = self.label.font()
        attrs = {NSFontAttributeName: font}
        label_width = self.FIXED_WIDTH - self.H_PADDING

        # Calculate bounding rect for text with constrained width
        ns_string = NSString.stringWithString_(text)
        text_size = ns_string.sizeWithAttributes_(attrs)

        # Estimate number of lines needed
        lines_needed = max(1, int(text_size.width / label_width) + 1)
        line_height = text_size.height
        required_text_height = lines_needed * line_height

        # Add padding for margins
        required_height = required_text_height + self.V_PADDING

        # Clamp between min and max
        new_height = max(self.MIN_HEIGHT, min(self.MAX_HEIGHT, required_height))

        # Get current frame
        current_frame = self.panel.frame()

        # Only resize if change is significant (avoid jitter)
        if abs(new_height - current_frame.size.height) > 10:
            # Keep window anchored at bottom (adjust y to grow upward)
            height_diff = new_height - current_frame.size.height
            new_y = current_frame.origin.y - height_diff

            # Update panel frame
            new_frame = NSMakeRect(
                current_frame.origin.x, new_y, self.FIXED_WIDTH, new_height
            )
            self.panel.setFrame_display_animate_(new_frame, True, True)

            # Update label height (keep at bottom with padding)
            label_height = new_height - self.V_PADDING
            self.label.setFrame_(NSMakeRect(15, 15, label_width, label_height))

            # Update close button position (top-right corner)
            self.close_button.setFrame_(
                NSMakeRect(self.FIXED_WIDTH - 35, new_height - 35, 25, 25)
            )

    def show(self):
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.orderFrontRegardless()
