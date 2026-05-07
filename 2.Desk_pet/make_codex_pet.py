from __future__ import annotations

import argparse
from collections import deque
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


COLUMNS = 8
ROWS = 9
CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_SIZE = (COLUMNS * CELL_WIDTH, ROWS * CELL_HEIGHT)
GREEN_MIN = 135


@dataclass(frozen=True)
class RowSpec:
    state: str
    row: int
    frame_count: int
    source_name: str
    mirror: bool = False


ROW_SPECS = [
    RowSpec("idle", 0, 6, "待机眨眼"),
    RowSpec("running-right", 1, 8, "监督工作"),
    RowSpec("running-left", 2, 8, "监督工作", mirror=True),
    RowSpec("waving", 3, 4, "监督工作"),
    RowSpec("jumping", 4, 5, "完成庆祝"),
    RowSpec("failed", 5, 8, "报错推手"),
    RowSpec("waiting", 6, 6, "困倦睡觉"),
    RowSpec("running", 7, 6, "敲代码"),
    RowSpec("review", 8, 6, "修Bug"),
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def remove_green_screen(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def offset(x: int, y: int) -> int:
        return y * width + x

    def is_chroma_pixel(x: int, y: int) -> bool:
        red, green, blue, alpha = pixels[x, y]
        if alpha == 0:
            return True
        strongest_non_green = max(red, blue)
        return (
            green >= GREEN_MIN
            and green - strongest_non_green >= 24
            and green >= red * 1.12
            and green >= blue * 1.12
        )

    for x in range(width):
        for y in (0, height - 1):
            if is_chroma_pixel(x, y):
                background[offset(x, y)] = 1
                queue.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if is_chroma_pixel(x, y) and not background[offset(x, y)]:
                background[offset(x, y)] = 1
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            index = offset(nx, ny)
            if not background[index] and is_chroma_pixel(nx, ny):
                background[index] = 1
                queue.append((nx, ny))

    for y in range(rgba.height):
        for x in range(rgba.width):
            if background[offset(x, y)]:
                red, green, blue, alpha = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)

    cleaned = rgba.copy()
    cleaned_pixels = cleaned.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            touches_background = False
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if pixels[nx, ny][3] == 0:
                    touches_background = True
                    break
            if touches_background and green > max(red, blue) + 12:
                cleaned_pixels[x, y] = (red, min(green, max(red, blue) + 10), blue, alpha)
    rgba = cleaned
    return rgba


def split_strip(path: Path) -> list[Image.Image]:
    with Image.open(path) as opened:
        strip = remove_green_screen(opened)

    frames = extract_component_frames(strip)
    if frames is not None:
        return frames

    if strip.width % 6 != 0:
        raise ValueError(f"{path.name} width {strip.width} is not divisible by 6")
    frame_width = strip.width // 6
    frames = []
    for index in range(6):
        left = index * frame_width
        frame = strip.crop((left, 0, left + frame_width, strip.height))
        frames.append(fit_to_cell(frame))
    return frames


def connected_components(image: Image.Image) -> list[dict[str, object]]:
    alpha = image.getchannel("A")
    width, height = image.size
    data = alpha.tobytes()
    visited = bytearray(width * height)
    components: list[dict[str, object]] = []

    for start, alpha_value in enumerate(data):
        if alpha_value <= 16 or visited[start]:
            continue

        stack = [start]
        visited[start] = 1
        pixels: list[int] = []
        min_x = width
        min_y = height
        max_x = 0
        max_y = 0

        while stack:
            current = stack.pop()
            pixels.append(current)
            x = current % width
            y = current // width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

            if x > 0:
                neighbor = current - 1
                if not visited[neighbor] and data[neighbor] > 16:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if x + 1 < width:
                neighbor = current + 1
                if not visited[neighbor] and data[neighbor] > 16:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if y > 0:
                neighbor = current - width
                if not visited[neighbor] and data[neighbor] > 16:
                    visited[neighbor] = 1
                    stack.append(neighbor)
            if y + 1 < height:
                neighbor = current + width
                if not visited[neighbor] and data[neighbor] > 16:
                    visited[neighbor] = 1
                    stack.append(neighbor)

        components.append(
            {
                "pixels": pixels,
                "area": len(pixels),
                "bbox": (min_x, min_y, max_x + 1, max_y + 1),
                "center_x": (min_x + max_x + 1) / 2,
            }
        )

    return components


def component_group_image(
    source: Image.Image,
    components: list[dict[str, object]],
    padding: int = 4,
) -> Image.Image:
    width, height = source.size
    min_x = max(0, min(component["bbox"][0] for component in components) - padding)
    min_y = max(0, min(component["bbox"][1] for component in components) - padding)
    max_x = min(width, max(component["bbox"][2] for component in components) + padding)
    max_y = min(height, max(component["bbox"][3] for component in components) + padding)

    output = Image.new("RGBA", (max_x - min_x, max_y - min_y), (0, 0, 0, 0))
    source_pixels = source.load()
    output_pixels = output.load()
    for component in components:
        for pixel_index in component["pixels"]:
            x = pixel_index % width
            y = pixel_index // width
            output_pixels[x - min_x, y - min_y] = source_pixels[x, y]
    return output


def extract_component_frames(strip: Image.Image) -> list[Image.Image] | None:
    components = connected_components(strip)
    if not components:
        return None

    seeds = []
    for component in components:
        left, top, right, bottom = component["bbox"]
        width = right - left
        height = bottom - top
        if width >= 80 and height >= 150 and component["area"] >= 1000:
            seeds.append(component)

    if len(seeds) < 2:
        return None

    seeds = sorted(seeds, key=lambda component: component["center_x"])
    seed_ids = {id(seed) for seed in seeds}
    groups: list[list[dict[str, object]]] = [[seed] for seed in seeds]
    largest_area = max(component["area"] for component in seeds)
    noise_threshold = max(16, largest_area * 0.002)

    for component in components:
        if id(component) in seed_ids or component["area"] < noise_threshold:
            continue
        nearest_index = min(
            range(len(seeds)),
            key=lambda index: abs(seeds[index]["center_x"] - component["center_x"]),
        )
        groups[nearest_index].append(component)

    return [fit_to_cell(component_group_image(strip, group)) for group in groups]


def fit_to_cell(frame: Image.Image) -> Image.Image:
    frame = keep_largest_component(frame)
    bbox = frame.getbbox()
    target = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    if bbox is None:
        return target

    sprite = frame.crop(bbox)
    max_width = CELL_WIDTH - 14
    max_height = CELL_HEIGHT - 10
    scale = min(max_width / sprite.width, max_height / sprite.height)
    new_size = (
        max(1, round(sprite.width * scale)),
        max(1, round(sprite.height * scale)),
    )
    sprite = sprite.resize(new_size, Image.Resampling.LANCZOS)

    left = (CELL_WIDTH - sprite.width) // 2
    top = CELL_HEIGHT - sprite.height - 5
    target.alpha_composite(sprite, (left, top))
    return target


def keep_largest_component(image: Image.Image) -> Image.Image:
    components = connected_components(image)
    if len(components) <= 1:
        return image

    largest = max(components, key=lambda component: component["area"])
    return component_group_image(image, [largest], padding=2)


def select_frames(frames: list[Image.Image], frame_count: int, mirror: bool) -> list[Image.Image]:
    source_count = len(frames)
    if source_count == frame_count:
        indexes = list(range(source_count))
    elif source_count > frame_count:
        if source_count == 8 and frame_count == 4:
            indexes = [0, 3, 5, 7]
        else:
            indexes = [
                round(index * (source_count - 1) / max(1, frame_count - 1))
                for index in range(frame_count)
            ]
    elif source_count > 1:
        ping_pong = list(range(source_count)) + list(range(source_count - 2, 0, -1))
        indexes = [ping_pong[index % len(ping_pong)] for index in range(frame_count)]
    else:
        indexes = [0] * frame_count

    selected = [frames[index].copy() for index in indexes]
    if mirror:
        selected = [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in selected]
    return selected


def compose_atlas(photo_dir: Path, output_dir: Path) -> Path:
    atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
    frames_root = output_dir / "frames"
    if frames_root.exists():
        shutil.rmtree(frames_root)
    frames_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    cache: dict[str, list[Image.Image]] = {}
    for spec in ROW_SPECS:
        source_path = photo_dir / f"{spec.source_name}.png"
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing source strip: {source_path}")
        if spec.source_name not in cache:
            cache[spec.source_name] = split_strip(source_path)

        row_frames = select_frames(cache[spec.source_name], spec.frame_count, spec.mirror)
        state_dir = frames_root / spec.state
        state_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = []
        for column, frame in enumerate(row_frames):
            atlas.alpha_composite(frame, (column * CELL_WIDTH, spec.row * CELL_HEIGHT))
            frame_path = state_dir / f"{column:02d}.png"
            frame.save(frame_path)
            frame_paths.append(str(frame_path))
        manifest.append(
            {
                "state": spec.state,
                "row": spec.row,
                "source": spec.source_name,
                "frames": frame_paths,
                "mirrored": spec.mirror,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    atlas_path = output_dir / "spritesheet.png"
    webp_path = output_dir / "spritesheet.webp"
    atlas.save(atlas_path)
    atlas.save(webp_path, format="WEBP", lossless=True, quality=100, method=6)
    (output_dir / "build-manifest.json").write_text(
        json.dumps({"ok": True, "atlas": str(atlas_path), "rows": manifest}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return atlas_path


def package_pet(atlas_path: Path, pet_dir: Path, pet_id: str, display_name: str) -> None:
    pet_dir.mkdir(parents=True, exist_ok=True)
    target_sheet = pet_dir / "spritesheet.webp"
    with Image.open(atlas_path) as atlas:
        atlas.save(target_sheet, format="WEBP", lossless=True, quality=100, method=6)

    manifest = {
        "id": pet_id,
        "displayName": display_name,
        "description": "A chibi coding companion made from the provided desktop pet action strips.",
        "spritesheetPath": "spritesheet.webp",
    }
    (pet_dir / "pet.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Codex custom pet from 6-frame action strips.")
    parser.add_argument("--photo-dir", type=Path, default=Path("photo"))
    parser.add_argument("--output-dir", type=Path, default=Path("codex-pet-build"))
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--repo-package-root", type=Path, default=Path("codex-pet"))
    parser.add_argument("--pet-name", default="desk-boy")
    parser.add_argument("--display-name", default="Desk Boy")
    args = parser.parse_args()

    pet_id = slugify(args.pet_name)
    if not pet_id:
        raise ValueError("pet name must contain at least one ASCII letter or digit")

    atlas_path = compose_atlas(args.photo_dir.resolve(), args.output_dir.resolve())
    codex_pet_dir = args.codex_home.resolve() / "pets" / pet_id
    repo_pet_dir = args.repo_package_root.resolve() / pet_id
    package_pet(atlas_path, codex_pet_dir, pet_id, args.display_name)
    package_pet(atlas_path, repo_pet_dir, pet_id, args.display_name)
    print(
        json.dumps(
            {
                "ok": True,
                "atlas": str(atlas_path),
                "codex_pet_dir": str(codex_pet_dir),
                "repo_pet_dir": str(repo_pet_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
