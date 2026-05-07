#!/usr/bin/env python3
"""Build a Codex pet from Wisdel source GIFs by direct pixelization."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageSequence


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_SIZE = (CELL_WIDTH * ATLAS_COLUMNS, CELL_HEIGHT * ATLAS_ROWS)
MAX_BODY_WIDTH = 180
TARGET_BODY_HEIGHT = 188
MAX_BODY_HEIGHT = 196
BOTTOM_PADDING = 6
PIXEL_BLOCK = 3

WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(
    "/Users/lawrenclia/Documents/otaxio/digit_maid/resource/wisdel/皮肤素材/可用素材"
)
SOURCE_SHEET = (
    WORKSPACE
    / "references"
    / "maidbit-materials"
    / "available-materials-reference-sheet.png"
)
RUN_DIR = WORKSPACE / "output" / "hatch-pet" / "wisdel-pixel-direct"
HATCH_SCRIPTS = Path("/Users/lawrenclia/.codex/skills/hatch-pet/scripts")


@dataclass(frozen=True)
class RowSpec:
    state: str
    source: str
    frame_count: int
    row_index: int
    sample: str = "even"
    mirror_from: str | None = None
    indices: tuple[int, ...] | None = None
    motion_x: float = 0.0
    motion_y: float = 0.0


ROW_SPECS = [
    RowSpec("idle", "interact.gif", 6, 0, indices=(0, 4, 12, 24, 40, 45), motion_y=0.12),
    RowSpec("running-right", "move.gif", 8, 1, motion_x=0.10, motion_y=0.18),
    RowSpec("running-left", "move.gif", 8, 2, mirror_from="running-right"),
    RowSpec("waving", "fly.gif", 4, 3, indices=(0, 8, 18, 34), motion_x=0.12, motion_y=0.15),
    RowSpec("jumping", "jump.gif", 5, 4, indices=(0, 8, 17, 32, 41), motion_y=0.55),
    RowSpec("failed", "die.gif", 8, 5, motion_x=0.12, motion_y=0.16),
    RowSpec("waiting", "sit.gif", 6, 6, motion_y=0.10),
    RowSpec("running", "special.gif", 6, 7, motion_x=0.12, motion_y=0.18),
    RowSpec("review", "special1.gif", 6, 8, indices=(10, 14, 18, 22, 28, 34), motion_y=0.10),
]


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def rgba_frames(path: Path) -> list[Image.Image]:
    with Image.open(path) as opened:
        frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(opened)]
    return frames


def alpha_bbox(image: Image.Image, threshold: int = 8) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A").point(lambda value: 255 if value > threshold else 0)
    return alpha.getbbox()


def union_bbox(frames: list[Image.Image]) -> tuple[int, int, int, int]:
    boxes = [box for box in (alpha_bbox(frame) for frame in frames) if box is not None]
    if not boxes:
        return (0, 0, 1, 1)
    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    max_x = max(box[2] for box in boxes)
    max_y = max(box[3] for box in boxes)
    return (min_x, min_y, max_x, max_y)


def padded_bbox(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
    padding: int,
) -> tuple[int, int, int, int]:
    return (
        max(0, box[0] - padding),
        max(0, box[1] - padding),
        min(image_size[0], box[2] + padding),
        min(image_size[1], box[3] + padding),
    )


def evenly_spaced_indices(total: int, count: int) -> list[int]:
    if count <= 1:
        return [0]
    if total <= count:
        return list(range(total)) + [total - 1] * (count - total)
    return [round(index * (total - 1) / (count - 1)) for index in range(count)]


def fit_size(size: tuple[int, int], max_size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    scale = min(max_size[0] / width, max_size[1] / height, 1.0)
    return (max(1, round(width * scale)), max(1, round(height * scale)))


def pixelize(image: Image.Image, block: int = PIXEL_BLOCK) -> Image.Image:
    width, height = image.size
    small = image.resize(
        (max(1, width // block), max(1, height // block)),
        Image.Resampling.BOX,
    )
    return small.resize((width, height), Image.Resampling.NEAREST)


def stable_fit_size(size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    scale = min(
        MAX_BODY_WIDTH / width,
        TARGET_BODY_HEIGHT / height,
        MAX_BODY_HEIGHT / height,
        1.0 if height >= TARGET_BODY_HEIGHT else TARGET_BODY_HEIGHT / height,
    )
    return (max(1, round(width * scale)), max(1, round(height * scale)))


def frame_to_cell(
    frame: Image.Image,
    *,
    motion_offset: tuple[int, int] = (0, 0),
) -> Image.Image:
    box = alpha_bbox(frame)
    if box is None:
        return Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    crop = frame.crop(padded_bbox(box, frame.size, padding=2))
    fitted_size = stable_fit_size(crop.size)
    crop = crop.resize(fitted_size, Image.Resampling.LANCZOS)
    crop = pixelize(crop)
    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    left = (CELL_WIDTH - crop.width) // 2 + motion_offset[0]
    top = CELL_HEIGHT - BOTTOM_PADDING - crop.height + motion_offset[1]
    left = max(0, min(CELL_WIDTH - crop.width, left))
    top = max(0, min(CELL_HEIGHT - crop.height, top))
    cell.alpha_composite(crop, (left, top))
    return cell


def motion_offsets(frames: list[Image.Image], spec: RowSpec) -> list[tuple[int, int]]:
    if spec.motion_x == 0 and spec.motion_y == 0:
        return [(0, 0)] * len(frames)
    boxes = [alpha_bbox(frame) for frame in frames]
    valid = [box for box in boxes if box is not None]
    if not valid:
        return [(0, 0)] * len(frames)
    centers_x = [(box[0] + box[2]) / 2 for box in valid]
    centers_y = [(box[1] + box[3]) / 2 for box in valid]
    base_x = sum(centers_x) / len(centers_x)
    base_y = sum(centers_y) / len(centers_y)
    offsets = []
    for box in boxes:
        if box is None:
            offsets.append((0, 0))
            continue
        center_x = (box[0] + box[2]) / 2
        center_y = (box[1] + box[3]) / 2
        offsets.append(
            (
                round((center_x - base_x) * spec.motion_x),
                round((center_y - base_y) * spec.motion_y),
            )
        )
    return offsets


def make_row_frames(spec: RowSpec, frames_root: Path) -> dict[str, object]:
    source_path = SOURCE_DIR / spec.source
    all_frames = rgba_frames(source_path)
    indices = list(spec.indices) if spec.indices else evenly_spaced_indices(len(all_frames), spec.frame_count)
    if len(indices) != spec.frame_count:
        raise SystemExit(f"{spec.state} needs {spec.frame_count} indices, got {len(indices)}")
    selected = [all_frames[index] for index in indices]
    offsets = motion_offsets(selected, spec)
    state_dir = frames_root / spec.state
    state_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for column, frame in enumerate(selected):
        cell = frame_to_cell(frame, motion_offset=offsets[column])
        output = state_dir / f"{column:02d}.png"
        cell.save(output)
        outputs.append(str(output))
    return {
        "state": spec.state,
        "source": str(source_path),
        "source_frame_count": len(all_frames),
        "selected_indices": indices,
        "motion_offsets": offsets,
        "scaling": {
            "mode": "stable-source-bbox",
            "target_body_height": TARGET_BODY_HEIGHT,
            "max_body_width": MAX_BODY_WIDTH,
            "bottom_padding": BOTTOM_PADDING,
        },
        "frames": outputs,
        "method": "source-gif-pixelized",
    }


def mirror_row(source_state: str, target_state: str, frames_root: Path, count: int) -> dict[str, object]:
    source_dir = frames_root / source_state
    target_dir = frames_root / target_state
    target_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for column in range(count):
        source = source_dir / f"{column:02d}.png"
        with Image.open(source) as opened:
            mirrored = opened.convert("RGBA").transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        output = target_dir / f"{column:02d}.png"
        mirrored.save(output)
        outputs.append(str(output))
    return {
        "state": target_state,
        "source": source_state,
        "frames": outputs,
        "method": "source-gif-pixelized-mirror",
    }


def pixelize_reference_sheet(qa_dir: Path) -> Path | None:
    if not SOURCE_SHEET.is_file():
        return None
    with Image.open(SOURCE_SHEET) as opened:
        source = opened.convert("RGBA")
    output = qa_dir / "source-sheet-pixelized.png"
    pixelize(source, block=3).save(output)
    return output


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))
    return subprocess.run(command, check=check, text=True)


def write_request() -> None:
    request = {
        "pet_id": "wisdel",
        "display_name": "Wisdel",
        "description": (
            "A directly pixelized Wisdel desktop companion built from the supplied "
            "digit_maid GIF materials."
        ),
        "source_mode": "direct-source-gif-pixelization",
        "source_dir": str(SOURCE_DIR),
    }
    (RUN_DIR / "pet_request.json").write_text(
        json.dumps(request, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    decoded_dir = RUN_DIR / "decoded"
    frames_root = RUN_DIR / "frames"
    final_dir = RUN_DIR / "final"
    qa_dir = RUN_DIR / "qa"
    package_dir = WORKSPACE / "output" / "hatch-pet" / "wisdel-pixel-direct-package"

    clean_dir(RUN_DIR)
    clean_dir(package_dir)
    for path in (decoded_dir, frames_root, final_dir, qa_dir):
        path.mkdir(parents=True, exist_ok=True)

    write_request()
    pixelized_sheet = pixelize_reference_sheet(qa_dir)

    manifest_rows: list[dict[str, object]] = []
    specs_by_state = {spec.state: spec for spec in ROW_SPECS}
    for spec in ROW_SPECS:
        if spec.mirror_from:
            continue
        manifest_rows.append(make_row_frames(spec, frames_root))
    for spec in ROW_SPECS:
        if spec.mirror_from:
            manifest_rows.append(
                mirror_row(spec.mirror_from, spec.state, frames_root, spec.frame_count)
            )

    manifest_rows.sort(key=lambda row: specs_by_state[str(row["state"])].row_index)
    (frames_root / "frames-manifest.json").write_text(
        json.dumps(
            {
                "ok": True,
                "pixelization": {
                    "block": PIXEL_BLOCK,
                    "preserve_source_eyes": True,
                    "stable_hover_size": True,
                },
                "rows": manifest_rows,
                "source_sheet_pixelized": str(pixelized_sheet) if pixelized_sheet else None,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    review_path = qa_dir / "review.json"
    run(
        [
            sys.executable,
            str(HATCH_SCRIPTS / "inspect_frames.py"),
            "--frames-root",
            str(frames_root),
            "--json-out",
            str(review_path),
        ],
        check=False,
    )
    run(
        [
            sys.executable,
            str(HATCH_SCRIPTS / "compose_atlas.py"),
            "--frames-root",
            str(frames_root),
            "--output",
            str(final_dir / "spritesheet.png"),
            "--webp-output",
            str(final_dir / "spritesheet.webp"),
        ]
    )
    run(
        [
            sys.executable,
            str(HATCH_SCRIPTS / "validate_atlas.py"),
            str(final_dir / "spritesheet.webp"),
            "--json-out",
            str(final_dir / "validation.json"),
        ]
    )
    run(
        [
            sys.executable,
            str(HATCH_SCRIPTS / "make_contact_sheet.py"),
            str(final_dir / "spritesheet.webp"),
            "--output",
            str(qa_dir / "contact-sheet.png"),
        ]
    )
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        run(
            [
                sys.executable,
                str(HATCH_SCRIPTS / "render_animation_videos.py"),
                str(final_dir / "spritesheet.webp"),
                "--output-dir",
                str(qa_dir / "videos"),
                "--ffmpeg",
                ffmpeg,
            ]
        )

    run(
        [
            sys.executable,
            str(HATCH_SCRIPTS / "package_custom_pet.py"),
            "--pet-name",
            "wisdel",
            "--display-name",
            "Wisdel",
            "--description",
            "A directly pixelized Wisdel desktop companion built from the supplied digit_maid GIF materials.",
            "--spritesheet",
            str(final_dir / "spritesheet.webp"),
            "--output-dir",
            str(package_dir),
            "--force",
        ]
    )

    summary = {
        "ok": True,
        "run_dir": str(RUN_DIR),
        "package": str(package_dir),
        "spritesheet": str(final_dir / "spritesheet.webp"),
        "contact_sheet": str(qa_dir / "contact-sheet.png"),
        "review": str(review_path),
        "validation": str(final_dir / "validation.json"),
        "videos": str(qa_dir / "videos") if ffmpeg else None,
        "source_sheet_pixelized": str(pixelized_sheet) if pixelized_sheet else None,
    }
    (qa_dir / "run-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
