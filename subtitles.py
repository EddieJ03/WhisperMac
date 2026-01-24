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

        self.prev_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 50, label_width, 30)
        )
        self.prev_label.setTextColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0.8, 0.8, 0.8)
        )
        self.prev_label.setFont_(NSFont.systemFontOfSize_weight_(20, 0.4))
        self.prev_label.setBezeled_(False)
        self.prev_label.setDrawsBackground_(False)
        self.prev_label.setEditable_(False)
        self.prev_label.setSelectable_(False)
        self.prev_label.setAlignment_(NSTextAlignmentCenter)
        self.prev_label.setLineBreakMode_(NSLineBreakByWordWrapping)
        content_view.addSubview_(self.prev_label)

        # Create current line label (larger, bright)
        self.label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(15, 15, label_width, 40)
        )
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

    def setText_(self, texts):
        """Called on main thread - update UI with previous and current text"""
        prev_text, curr_text = texts
        self.prev_label.setStringValue_(prev_text)
        self.label.setStringValue_(curr_text)
        self._resize_for_text(prev_text, curr_text)

    def set_text_with_previous(self, prev_text, curr_text):
        """Thread-safe: schedules UI update on main thread with both texts"""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(self.setText_, signature=b"v@:@"),
            (prev_text, curr_text),
            False,  # Don't block the calling thread
        )

    def set_text(self, text):
        """Thread-safe: schedules UI update on main thread (legacy, for backwards compatibility)"""
        self.set_text_with_previous("", text)

    def _resize_for_text(self, prev_text, curr_text):
        """Resize window height to fit wrapped text content"""
        label_width = self.FIXED_WIDTH - self.H_PADDING

        # Calculate height for current text (larger font)
        curr_font = self.label.font()
        curr_attrs = {NSFontAttributeName: curr_font}
        ns_curr = NSString.stringWithString_(curr_text)
        curr_size = ns_curr.sizeWithAttributes_(curr_attrs)
        curr_lines = max(1, int(curr_size.width / label_width) + 1)
        curr_height = curr_lines * curr_size.height

        # Calculate height for previous text (smaller font)
        prev_height = 0
        spacing = 0
        if prev_text:
            prev_font = self.prev_label.font()
            prev_attrs = {NSFontAttributeName: prev_font}
            ns_prev = NSString.stringWithString_(prev_text)
            prev_size = ns_prev.sizeWithAttributes_(prev_attrs)
            prev_lines = max(1, int(prev_size.width / label_width) + 1)
            prev_height = prev_lines * prev_size.height
            spacing = 10  # Add spacing between lines

        required_text_height = prev_height + spacing + curr_height

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
            self.panel.setFrame_display_animate_(new_frame, True, False)

            # Update label positions (previous at top, current below)
            top_padding = 15
            if prev_text:
                # Previous label at top
                self.prev_label.setFrame_(
                    NSMakeRect(
                        15, new_height - 15 - prev_height, label_width, prev_height
                    )
                )
                # Current label below previous with spacing
                curr_label_y = new_height - 15 - prev_height - spacing - curr_height
                self.label.setFrame_(
                    NSMakeRect(15, curr_label_y, label_width, curr_height)
                )
            else:
                # No previous text, center current label
                self.prev_label.setFrame_(NSMakeRect(15, 15, label_width, 0))
                curr_label_y = new_height - 15 - curr_height
                self.label.setFrame_(
                    NSMakeRect(15, curr_label_y, label_width, curr_height)
                )

            # Update close button position (top-right corner)
            self.close_button.setFrame_(
                NSMakeRect(self.FIXED_WIDTH - 35, new_height - 35, 25, 25)
            )

    def show(self):
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.orderFrontRegardless()
