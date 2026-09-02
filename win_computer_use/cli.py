import argparse
import sys
import json
import time
from .client import ComputerUseClient
from .cursor import restore_system_cursor

def main():
    parser = argparse.ArgumentParser(description="Windows Computer Use Automation CLI (backed by OpenAI CUA)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    p_list = subparsers.add_parser("list", help="List active targetable windows")
    p_list.add_argument("--all", action="store_true", help="Include background and system handles")

    # activate
    p_act = subparsers.add_parser("activate", help="Bring window to foreground")
    p_act.add_argument("target", help="Window title substring or HWND ID")

    # click
    p_click = subparsers.add_parser("click", help="Click coordinates inside window")
    p_click.add_argument("target", help="Window title substring or HWND ID")
    p_click.add_argument("--x", type=int, required=True, help="X coordinate")
    p_click.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_click.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_click.add_argument("--count", type=int, default=1)

    # click-center
    p_center = subparsers.add_parser("click-center", help="Click at the geometric center of the window")
    p_center.add_argument("target", help="Window title substring or HWND ID")
    p_center.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_center.add_argument("--count", type=int, default=1)

    # type
    p_type = subparsers.add_parser("type", help="Type text into window focus")
    p_type.add_argument("target", help="Window title substring or HWND ID")
    p_type.add_argument("text", help="Text to type")

    # press
    p_press = subparsers.add_parser("press", help="Press key or chord (e.g. Return, Tab, Control_L+a)")
    p_press.add_argument("target", help="Window title substring or HWND ID")
    p_press.add_argument("key", help="Key or chord")

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Capture window screenshot to PNG file")
    p_shot.add_argument("target", help="Window title substring or HWND ID")
    p_shot.add_argument("--out", default="screenshot.png", help="Output PNG path")

    # cycle
    p_cycle = subparsers.add_parser("cycle", help="Cycle through all active windows with a delay")
    p_cycle.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between activations")

    # restore-cursor
    p_cursor = subparsers.add_parser("restore-cursor", help="Emergency restore of hidden mouse cursor")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "restore-cursor":
        res = restore_system_cursor()
        print("Cursor restored:", res)
        sys.exit(0)

    with ComputerUseClient() as cua:
        if args.command == "list":
            windows = cua.list_windows(filter_system=not args.all)
            print(f"Found {len(windows)} windows:")
            for i, w in enumerate(windows, 1):
                print(f" {i:2d}. [HWND {w['id']}] {w['title']}")

        elif args.command == "activate":
            w = cua.find_window(args.target)
            if not w:
                print(f"Window matching '{args.target}' not found.")
                sys.exit(1)
            cua.activate_window(w)
            print(f"Activated: {w['title']}")

        elif args.command == "click":
            cua.click(args.target, args.x, args.y, mouse_button=args.button, click_count=args.count)
            print(f"Clicked at ({args.x}, {args.y}) in '{args.target}'")

        elif args.command == "click-center":
            res = cua.click_center(args.target, mouse_button=args.button, click_count=args.count)
            print(f"Clicked center at ({res['x']}, {res['y']}) in '{res['window']}'")

        elif args.command == "type":
            cua.type_text(args.target, args.text)
            print(f"Typed '{args.text}' into '{args.target}'")

        elif args.command == "press":
            cua.press_key(args.target, args.key)
            print(f"Pressed '{args.key}' in '{args.target}'")

        elif args.command == "screenshot":
            meta = cua.save_screenshot(args.target, args.out)
            print(f"Screenshot saved to: {meta['path']} ({meta['width']}x{meta['height']})")

        elif args.command == "cycle":
            windows = cua.list_windows()
            print(f"Cycling through {len(windows)} windows (delay: {args.delay}s)...")
            for i, w in enumerate(windows, 1):
                print(f"[{i}/{len(windows)}] {w['title'][:60]}")
                cua.activate_window(w)
                time.sleep(args.delay)
            print("Cycling complete.")

if __name__ == "__main__":
    main()
