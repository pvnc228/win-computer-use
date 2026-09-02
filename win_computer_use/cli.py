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
    p_shot.add_argument("--crop", default="", help="Crop box: x,y,w,h (e.g. 100,200,300,300)")

    # scroll
    p_scroll = subparsers.add_parser("scroll", help="Scroll at coordinates inside window")
    p_scroll.add_argument("target", help="Window title substring or HWND ID")
    p_scroll.add_argument("--x", type=int, required=True, help="X coordinate")
    p_scroll.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_scroll.add_argument("--scroll-x", type=int, default=0, help="Horizontal scroll offset")
    p_scroll.add_argument("--scroll-y", type=int, default=600, help="Vertical scroll offset")

    # drag
    p_drag = subparsers.add_parser("drag", help="Drag mouse from coordinates to coordinates")
    p_drag.add_argument("target", help="Window title substring or HWND ID")
    p_drag.add_argument("--from-x", type=int, required=True, help="Start X")
    p_drag.add_argument("--from-y", type=int, required=True, help="Start Y")
    p_drag.add_argument("--to-x", type=int, required=True, help="End X")
    p_drag.add_argument("--to-y", type=int, required=True, help="End Y")

    # aim (FPS / 3D camera)
    p_aim = subparsers.add_parser("aim", help="Relative mouse delta for 3D games / FPS aiming")
    p_aim.add_argument("target", nargs="?", default="", help="Window title substring or HWND ID")
    p_aim.add_argument("--dx", type=int, required=True, help="Delta X")
    p_aim.add_argument("--dy", type=int, required=True, help="Delta Y")

    # hold (WASD movement)
    p_hold = subparsers.add_parser("hold", help="Hold keyboard key down with hardware scan codes")
    p_hold.add_argument("target", nargs="?", default="", help="Window title substring or HWND ID")
    p_hold.add_argument("--key", required=True, help="Key name (w, a, s, d, shift, space, etc.)")
    p_hold.add_argument("--duration", type=float, default=0.5, help="Duration in seconds")

    # mouse-down
    p_mdown = subparsers.add_parser("mouse-down", help="Press and hold mouse button")
    p_mdown.add_argument("target", nargs="?", default="", help="Window title substring or HWND ID")
    p_mdown.add_argument("--button", default="left", choices=["left", "right", "middle"])

    # mouse-up
    p_mup = subparsers.add_parser("mouse-up", help="Release mouse button")
    p_mup.add_argument("target", nargs="?", default="", help="Window title substring or HWND ID")
    p_mup.add_argument("--button", default="left", choices=["left", "right", "middle"])

    # shoot
    p_shoot = subparsers.add_parser("shoot", help="Fire weapon burst (hold mouse button for duration)")
    p_shoot.add_argument("target", nargs="?", default="", help="Window title substring or HWND ID")
    p_shoot.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_shoot.add_argument("--duration", type=float, default=0.15, help="Burst duration in seconds")

    # macro
    p_macro = subparsers.add_parser("macro", help="Execute an atomic JSON action sequence")
    p_macro.add_argument("actions", help="JSON string or path to .json file containing actions list")
    p_macro.add_argument("--target", default="", help="Optional window title or HWND to activate first")

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
            if args.crop:
                try:
                    cx, cy, cw, ch = [int(v.strip()) for v in args.crop.split(",")]
                    from PIL import Image
                    with Image.open(meta['path']) as img:
                        cropped = img.crop((cx, cy, cx + cw, cy + ch))
                        cropped.save(meta['path'])
                    print(f"Screenshot cropped to ({cx},{cy},{cw},{ch}) and saved to: {meta['path']}")
                except Exception as e:
                    print(f"Failed to crop screenshot: {e}")
            else:
                print(f"Screenshot saved to: {meta['path']} ({meta['width']}x{meta['height']})")

        elif args.command == "scroll":
            cua.scroll(args.target, args.x, args.y, scroll_x=args.scroll_x, scroll_y=args.scroll_y)
            print(f"Scrolled at ({args.x}, {args.y}) in '{args.target}'")

        elif args.command == "drag":
            cua.drag(args.target, args.from_x, args.from_y, args.to_x, args.to_y)
            print(f"Dragged from ({args.from_x}, {args.from_y}) to ({args.to_x}, {args.to_y}) in '{args.target}'")

        elif args.command == "aim":
            res = cua.aim(args.target if args.target else None, args.dx, args.dy)
            print(f"Aim moved relative dx={args.dx}, dy={args.dy}: {res}")

        elif args.command == "hold":
            res = cua.hold_key(args.target if args.target else None, args.key, args.duration)
            print(f"Held key '{args.key}' for {args.duration}s: {res}")

        elif args.command == "mouse-down":
            res = cua.mouse_down(args.target if args.target else None, args.button)
            print(f"Mouse button '{args.button}' down: {res}")

        elif args.command == "mouse-up":
            res = cua.mouse_up(args.target if args.target else None, args.button)
            print(f"Mouse button '{args.button}' up: {res}")

        elif args.command == "shoot":
            res = cua.shoot(args.target if args.target else None, args.button, args.duration)
            print(f"Fired weapon burst ({args.button}, {args.duration}s): {res}")

        elif args.command == "macro":
            import os
            raw_act = args.actions
            if os.path.exists(raw_act):
                with open(raw_act, "r", encoding="utf-8") as f:
                    act_list = json.load(f)
            else:
                act_list = json.loads(raw_act)
            results = cua.run_macro(args.target if args.target else None, act_list)
            print("Macro execution completed:")
            for r in results:
                print(" ", r)

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
