from __future__ import annotations

import argparse
import json
import random
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk


TRANSPARENT_COLOR = "#010203"
CELL_WIDTH = 192
CELL_HEIGHT = 208
PET_ID = "desk-boy"


@dataclass(frozen=True)
class AnimationSpec:
    state: str
    row: int
    frame_count: int
    durations: tuple[int, ...]
    label: str


ANIMATIONS = [
    AnimationSpec("idle", 0, 6, (280, 110, 110, 140, 140, 320), "待机"),
    AnimationSpec("running-right", 1, 8, (120, 120, 120, 120, 120, 120, 120, 220), "向右移动"),
    AnimationSpec("running-left", 2, 8, (120, 120, 120, 120, 120, 120, 120, 220), "向左移动"),
    AnimationSpec("waving", 3, 4, (140, 140, 140, 280), "挥手"),
    AnimationSpec("jumping", 4, 5, (140, 140, 140, 140, 280), "庆祝"),
    AnimationSpec("failed", 5, 8, (140, 140, 140, 140, 140, 140, 140, 240), "报错"),
    AnimationSpec("waiting", 6, 6, (150, 150, 150, 150, 150, 260), "等待"),
    AnimationSpec("running", 7, 6, (120, 120, 120, 120, 120, 220), "工作中"),
    AnimationSpec("review", 8, 6, (150, 150, 150, 150, 150, 280), "修 Bug"),
]

ANIMATION_BY_STATE = {animation.state: animation for animation in ANIMATIONS}
DEFAULT_STATE = "idle"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def find_pet_dir() -> Path:
    candidates = [
        app_base_dir() / "codex-pet" / PET_ID,
        Path(sys.executable).resolve().parent / "codex-pet" / PET_ID,
        Path.cwd() / "codex-pet" / PET_ID,
    ]
    for candidate in candidates:
        if (candidate / "spritesheet.webp").is_file():
            return candidate
    raise FileNotFoundError("Cannot find codex-pet/desk-boy/spritesheet.webp.")


class DesktopPet:
    def __init__(self, root: tk.Tk, pet_dir: Path, scale: float, idle_random: bool) -> None:
        self.root = root
        self.pet_dir = pet_dir
        self.scale = max(0.5, min(scale, 4.0))
        self.idle_random = idle_random
        self.state = DEFAULT_STATE
        self.frame_index = 0
        self.after_id: str | None = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.loop_count = 0

        self.frames = self.load_frames()

        self.root.title(self.display_name())
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)

        self.label = tk.Label(
            self.root,
            bg=TRANSPARENT_COLOR,
            bd=0,
            highlightthickness=0,
            takefocus=False,
        )
        self.label.pack()
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.drag)
        self.label.bind("<Button-3>", self.show_menu)
        self.label.bind("<Double-Button-1>", lambda _event: self.set_state("running"))

        self.menu = tk.Menu(self.root, tearoff=False)
        for animation in ANIMATIONS:
            self.menu.add_command(
                label=animation.label,
                command=lambda state=animation.state: self.set_state(state),
            )
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

        self.place_initially()
        self.play()

    def display_name(self) -> str:
        manifest_path = self.pet_dir / "pet.json"
        if not manifest_path.is_file():
            return "Desk Boy"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "Desk Boy"
        return str(manifest.get("displayName") or "Desk Boy")

    def load_frames(self) -> dict[str, list[ImageTk.PhotoImage]]:
        atlas_path = self.pet_dir / "spritesheet.webp"
        with Image.open(atlas_path) as opened:
            atlas = opened.convert("RGBA")

        frames: dict[str, list[ImageTk.PhotoImage]] = {}
        for animation in ANIMATIONS:
            state_frames = []
            for column in range(animation.frame_count):
                left = column * CELL_WIDTH
                top = animation.row * CELL_HEIGHT
                frame = atlas.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT))
                if self.scale != 1.0:
                    frame = frame.resize(
                        (
                            max(1, round(frame.width * self.scale)),
                            max(1, round(frame.height * self.scale)),
                        ),
                        Image.Resampling.NEAREST,
                    )
                state_frames.append(ImageTk.PhotoImage(frame))
            frames[animation.state] = state_frames
        return frames

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
        animation = ANIMATION_BY_STATE[self.state]
        frames = self.frames[self.state]
        self.label.configure(image=frames[self.frame_index])

        delay = animation.durations[self.frame_index]
        self.frame_index = (self.frame_index + 1) % animation.frame_count
        if self.frame_index == 0:
            self.loop_count += 1
            if self.idle_random and self.state == "idle" and self.loop_count % 8 == 0:
                self.set_state(random.choice(["waiting", "review", "running"]))

        self.after_id = self.root.after(delay, self.play)

    def set_state(self, state: str) -> None:
        if state not in self.frames:
            return
        self.state = state
        self.frame_index = 0
        self.loop_count = 0

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
    parser = argparse.ArgumentParser(description="A Windows desktop pet powered by a Codex-style atlas.")
    parser.add_argument("--pet-dir", type=Path, default=None, help="Folder containing pet.json and spritesheet.webp.")
    parser.add_argument("--scale", type=float, default=1.35, help="Display scale for 192x208 Codex cells.")
    parser.add_argument("--idle-random", action="store_true", help="Occasionally switch from idle to another state.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = tk.Tk()
    try:
        pet_dir = args.pet_dir.resolve() if args.pet_dir is not None else find_pet_dir()
        DesktopPet(root, pet_dir, args.scale, args.idle_random)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("DeskPet", str(exc))
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
