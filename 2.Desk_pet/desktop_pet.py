from __future__ import annotations

import argparse
import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


FRAME_COUNT = 6
DEFAULT_ACTION = "待机眨眼"
CHROMA_KEY = "#00ff00"
DEFAULT_DELAY_MS = 180
DEFAULT_SUBSAMPLE = 2
GREEN_MIN = 170
RED_MAX = 90
BLUE_MAX = 90

ACTION_ORDER = [
    "待机眨眼",
    "偷看屏幕",
    "加载等待",
    "困倦睡觉",
    "完成庆祝",
    "修Bug",
    "报错推手",
    "敲代码",
    "监督工作",
]


class WindowRegion:
    RGN_OR = 2

    def __init__(self) -> None:
        self.enabled = sys.platform == "win32"
        if self.enabled:
            self.gdi32 = ctypes.windll.gdi32
            self.user32 = ctypes.windll.user32

    def apply(self, hwnd: int, runs: list[tuple[int, int, int]]) -> None:
        if not self.enabled:
            return

        region = self.gdi32.CreateRectRgn(0, 0, 0, 0)
        if not region:
            return

        for y, start_x, end_x in runs:
            rect = self.gdi32.CreateRectRgn(start_x, y, end_x, y + 1)
            if rect:
                self.gdi32.CombineRgn(region, region, rect, self.RGN_OR)
                self.gdi32.DeleteObject(rect)

        if not self.user32.SetWindowRgn(hwnd, region, True):
            self.gdi32.DeleteObject(region)


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def find_photo_dir() -> Path:
    candidates = [
        app_base_dir() / "photo",
        Path(sys.executable).resolve().parent / "photo",
        Path.cwd() / "photo",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Cannot find the photo folder next to the app.")


class DesktopPet:
    def __init__(self, root: tk.Tk, photo_dir: Path, subsample: int, delay_ms: int) -> None:
        self.root = root
        self.photo_dir = photo_dir
        self.subsample = max(1, subsample)
        self.delay_ms = max(40, delay_ms)
        self.action_paths: dict[str, Path] = {}
        self.actions: dict[str, list[tk.PhotoImage]] = {}
        self.action_masks: dict[str, list[list[tuple[int, int, int]]]] = {}
        self.current_action = DEFAULT_ACTION
        self.frame_index = 0
        self.after_id: str | None = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.window_region = WindowRegion()

        self.root.title("DeskPet")
        self.root.configure(bg=CHROMA_KEY)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.wm_attributes("-transparentcolor", CHROMA_KEY)
        except tk.TclError:
            pass

        self.label = tk.Label(
            self.root,
            bg=CHROMA_KEY,
            bd=0,
            highlightthickness=0,
            takefocus=False,
        )
        self.label.pack()
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.drag)
        self.label.bind("<Button-3>", self.show_menu)
        self.label.bind("<Double-Button-1>", self.next_action)

        self.menu = tk.Menu(self.root, tearoff=False)
        self.load_actions()
        self.build_menu()

        if DEFAULT_ACTION not in self.action_paths:
            self.current_action = next(iter(self.action_paths))
        self.ensure_action_loaded(self.current_action)

        self.place_initially()
        self.play()

    def load_actions(self) -> None:
        pngs = {path.stem: path for path in self.photo_dir.glob("*.png")}
        ordered_names = [name for name in ACTION_ORDER if name in pngs]
        ordered_names.extend(sorted(name for name in pngs if name not in ordered_names))

        for name in ordered_names:
            self.action_paths[name] = pngs[name]

        if not self.action_paths:
            raise FileNotFoundError(f"No PNG action strips found in {self.photo_dir}.")

    def ensure_action_loaded(self, action: str) -> None:
        if action not in self.actions:
            frames, masks = self.load_strip(self.action_paths[action])
            self.actions[action] = frames
            self.action_masks[action] = masks

    def load_strip(self, path: Path) -> tuple[list[tk.PhotoImage], list[list[tuple[int, int, int]]]]:
        strip = tk.PhotoImage(file=str(path))
        width = strip.width()
        height = strip.height()
        if width % FRAME_COUNT != 0:
            raise ValueError(f"{path.name} width {width} is not divisible by {FRAME_COUNT}.")

        frame_width = width // FRAME_COUNT
        frames: list[tk.PhotoImage] = []
        masks: list[list[tuple[int, int, int]]] = []
        for index in range(FRAME_COUNT):
            frame = tk.PhotoImage(width=frame_width, height=height)
            frame.tk.call(
                frame,
                "copy",
                strip,
                "-from",
                index * frame_width,
                0,
                (index + 1) * frame_width,
                height,
                "-to",
                0,
                0,
            )
            if self.subsample > 1:
                frame = frame.subsample(self.subsample, self.subsample)
            self.apply_chroma_transparency(frame)
            masks.append(self.build_opaque_runs(frame))
            frames.append(frame)
        return frames, masks

    def apply_chroma_transparency(self, image: tk.PhotoImage) -> None:
        # The source strips use a green-screen background with small RGB variation.
        image.tk.eval(
            f"""
            set img {str(image)}
            set width [image width $img]
            set height [image height $img]
            for {{set y 0}} {{$y < $height}} {{incr y}} {{
                for {{set x 0}} {{$x < $width}} {{incr x}} {{
                    lassign [$img get $x $y] r g b
                    if {{$g >= {GREEN_MIN} && $r <= {RED_MAX} && $b <= {BLUE_MAX}}} {{
                        $img transparency set $x $y 1
                    }}
                }}
            }}
            """
        )

    def build_opaque_runs(self, image: tk.PhotoImage) -> list[tuple[int, int, int]]:
        runs: list[tuple[int, int, int]] = []
        width = image.width()
        height = image.height()
        for y in range(height):
            start_x: int | None = None
            for x in range(width):
                is_opaque = not image.transparency_get(x, y)
                if is_opaque and start_x is None:
                    start_x = x
                elif not is_opaque and start_x is not None:
                    runs.append((y, start_x, x))
                    start_x = None
            if start_x is not None:
                runs.append((y, start_x, width))
        return runs

    def build_menu(self) -> None:
        for name in self.action_paths:
            self.menu.add_command(label=name, command=lambda action=name: self.set_action(action))
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

    def place_initially(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, screen_width - width - 80)
        y = max(0, screen_height - height - 120)
        self.root.geometry(f"+{x}+{y}")

    def play(self) -> None:
        frames = self.actions[self.current_action]
        masks = self.action_masks[self.current_action]
        frame_index = self.frame_index
        self.label.configure(image=frames[frame_index])
        self.window_region.apply(self.root.winfo_id(), masks[frame_index])
        self.frame_index = (self.frame_index + 1) % len(frames)
        self.after_id = self.root.after(self.delay_ms, self.play)

    def set_action(self, action: str) -> None:
        if action not in self.action_paths:
            return
        self.ensure_action_loaded(action)
        self.current_action = action
        self.frame_index = 0

    def next_action(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        names = list(self.action_paths)
        current = names.index(self.current_action)
        self.set_action(names[(current + 1) % len(names)])

    def start_drag(self, event: tk.Event[tk.Misc]) -> None:
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y

    def drag(self, event: tk.Event[tk.Misc]) -> None:
        x = event.x_root - self.drag_offset_x
        y = event.y_root - self.drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def show_menu(self, event: tk.Event[tk.Misc]) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)
        self.menu.grab_release()

    def quit(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A small Windows desktop pet.")
    parser.add_argument(
        "--photo-dir",
        type=Path,
        default=None,
        help="Folder containing 6-frame horizontal PNG action strips.",
    )
    parser.add_argument(
        "--subsample",
        type=int,
        default=DEFAULT_SUBSAMPLE,
        help="Integer image downscale factor. Use 1 for original size.",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=DEFAULT_DELAY_MS,
        help="Animation frame delay in milliseconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = tk.Tk()
    try:
        photo_dir = args.photo_dir if args.photo_dir is not None else find_photo_dir()
        DesktopPet(root, photo_dir.resolve(), args.subsample, args.delay)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("DeskPet", str(exc))
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
