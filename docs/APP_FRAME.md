# Pinned application frame

The document previously grew with each tab's content. The app now uses a
viewport-height grid with separate header, scrollable main and bottom-menu rows.
Only main scrolls; neither long bank/news pages nor Home content can displace
the navigation. Footer space is part of the layout, so the final item does not
sit behind the tabs. Safe-area insets and dynamic viewport height are retained.
Tab switches and nested Bank/Services navigation reset the main pane's scroll
position. The viewport requests keyboard-driven content resizing where supported.
The current theme and existing voice interactions are unchanged by this fix.

The opt-in `tests/check_app_frame.py` measures actual browser rectangles before
and after scrolling rather than checking CSS strings. It covers all four tabs,
long Home content, nested navigation, both languages, small/keyboard-sized and
desktop windows, and 200% text. It also verifies that every tab button remains
visible and unobstructed. Live checks passed; physical-device acceptance remains
separate. Asset version 45 refreshes cached shell resources.

```sh
/path/to/venv/bin/python tests/check_app_frame.py --base-url https://app.sumon.me
```
