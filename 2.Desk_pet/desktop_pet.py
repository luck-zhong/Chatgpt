from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


FRAME_COUNT = 6
DEFAULT_ACTION = "待机眨眼"
CHROMA_KEY = "#00ff00"
DEFAULT_DELAY_MS = 180
DEFAULT_SUBSAMPLE = 2

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
        self.actions: dict[str, list[tk.PhotoImage]] = {}
        self.current_action = DEFAULT_ACTION
        self.frame_index = 0
        self.after_id: str | None = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

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

        if DEFAULT_ACTION not in self.actions:
            self.current_action = next(iter(self.actions))

        self.place_initially()
        self.play()

    def load_actions(self) -> None:
        pngs = {path.stem: path for path in self.photo_dir.glob("*.png")}
        ordered_names = [name for name in ACTION_ORDER if name in pngs]
        ordered_names.extend(sorted(name for name in pngs if name not in ordered_names))

        for name in ordered_names:
            self.actions[name] = self.load_strip(pngs[name])

        if not self.actions:
            raise FileNotFoundError(f"No PNG action strips found in {self.photo_dir}.")

    def load_strip(self, path: Path) -> list[tk.PhotoImage]:
        strip = tk.PhotoImage(file=str(path))
        width = strip.width()
        height = strip.height()
        if width % FRAME_COUNT != 0:
            raise ValueError(f"{path.name} width {width} is not divisible by {FRAME_COUNT}.")

        frame_width = width // FRAME_COUNT
        frames: list[tk.PhotoImage] = []
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
            frames.append(frame)
        return frames

    def build_menu(self) -> None:
        for name in self.actions:
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
        self.label.configure(image=frames[self.frame_index])
        self.frame_index = (self.frame_index + 1) % len(frames)
        self.after_id = self.root.after(self.delay_ms, self.play)

    def set_action(self, action: str) -> None:
        if action not in self.actions:
            return
        self.current_action = action
        self.frame_index = 0

    def next_action(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        names = list(self.actions)
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
