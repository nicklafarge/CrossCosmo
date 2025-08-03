from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

import arcade

ColorTuple3 = tuple[int, int, int]
ColorTuple4 = tuple[int, int, int, int]
ColorList = list[int]
ColorInputs = str | ColorTuple3 | ColorTuple4 | ColorList


def _get_arcade_color(config_val: ColorInputs) -> arcade.color.Color:
    if isinstance(config_val, str):
        if not hasattr(arcade.color, config_val):
            raise ValueError(f"Color '{config_val}' not found in arcade.color")
        return getattr(arcade.color, config_val)
    elif isinstance(config_val, tuple) or isinstance(config_val, list):
        if len(config_val) == 3:
            return arcade.color.Color(config_val[0], config_val[1], config_val[2], 255)
        elif len(config_val) == 4:
            color_tuple = arcade.color.Color(*config_val)
        else:
            raise ValueError(f"Tuple must be length 3 or 4: {config_val}")

        return arcade.color.Color(*color_tuple)
    else:
        raise ValueError(f"Input value must be a string or tuple of ints (length 3 or 4). Found: '{config_val}'")


def _update_colors(values: dict[str, Any], color_vars: list[str]) -> dict[str, Any]:
    for c in color_vars:
        if c in values:
            values[c] = _get_arcade_color(values[c])
    return values


@dataclass(frozen=True)
class WindowConfig:
    """Window display settings."""

    width: int = 1600
    height: int = 900
    title: str = "CrossCosmos"

    @property
    def height_to_width_ratio(self):
        """Percent of the window that a square occupies."""
        return self.height / self.width


@dataclass(frozen=True)
class CursorConfig:
    """Cursor settings."""

    blink_frequency: int = 30
    color1: arcade.color.Color = arcade.color.BLACK
    color2: arcade.color.Color = arcade.color.DARK_GRAY
    width: int = 2
    height_factor: float = 0.37


@dataclass(frozen=True)
class GridConfig:
    """Grid layout settings."""

    top_margin: int = 20
    right_margin: int = 20
    left_margin: int = 20
    bottom_margin: int = 60
    inner_margin: int = 2

    updates_per_frame: int = 100

    cursor: CursorConfig = field(default_factory=CursorConfig)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "GridConfig":
        """Initializes from a dictionary, converting colors to tuples"""
        color_vars = [
            "invalid_cell_color",
            "default_cell_color",
            "selected_cell_color",
            "active_word_color",
            "grid_border_color",
            "blacked_text_color",
            "cell_background_color",
            "grid_background_color",
        ]
        values = _update_colors(values, color_vars)
        return cls(**values)


@dataclass(frozen=True)
class InfoConfig:
    """Info section layout settings."""

    font_size: float = 14
    background_color1: arcade.color.Color = (70, 70, 70)
    background_color2: arcade.color.Color = (50, 50, 50)


@dataclass(frozen=True)
class TextConfig:
    """Text configuration options"""

    grid_font_name = "Liberation Mono"
    word_list_font_name = "Liberation Mono"
    info_section_font_name = "Liberation Sans"


@dataclass(frozen=True)
class AdvancedConfig:
    """Advanced behavioral settings."""

    pass


@dataclass(frozen=True)
class ColorConfig:
    """Advanced behavioral settings.

    Colors list: https://api.arcade.academy/en/2.6.17/arcade.color.html
    """

    grid_border: arcade.color.Color = arcade.color.WHITE
    grid_background: arcade.color.Color = (105, 105, 105)

    invalid_cell: arcade.color.Color = arcade.color.BURGUNDY
    default_cell: arcade.color.Color = arcade.color.WHITE
    cell_background: ColorTuple4 = arcade.color.WHITE
    # selected_cell: arcade.color.Color = (130, 130, 130)
    # active_word: arcade.color.Color = (200, 200, 200)

    selected_cell: arcade.color.Color = (122, 134, 151)
    active_word: arcade.color.Color = (214, 224, 239)

    normal_text: arcade.color.Color = arcade.color.BLACK
    locked_text: arcade.color.Color = arcade.color.GIANTS_ORANGE  # cyan
    blacked_text: arcade.color.Color = arcade.color.BLACK
    number: arcade.color.Color = (105, 105, 105)
    search_text: ColorTuple4 = arcade.color.BLACK

    info_bar_background1: arcade.color.Color = (70, 70, 70)
    info_bar_background2: arcade.color.Color = (50, 50, 50)

    block_valid_highlight: arcade.color.Color = arcade.color.BUD_GREEN
    block_invalid_highlight: arcade.color.Color = arcade.color.BURGUNDY

    search_len: arcade.color.Color = arcade.color.DARK_ELECTRIC_BLUE

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ColorConfig":
        """Initializes from a dictionary, converting colors to tuples"""
        values = _update_colors(values, ["normal_color", "locked_color"])
        return cls(**values)


@dataclass(frozen=True)
class LayoutConfig:
    """Complete application configuration."""

    window: WindowConfig = field(default_factory=WindowConfig)
    grid: GridConfig = field(default_factory=GridConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)
    color: ColorConfig = field(default_factory=ColorConfig)
    info: InfoConfig = field(default_factory=InfoConfig)
    text: TextConfig = field(default_factory=TextConfig)

    @classmethod
    def from_toml(cls, path: Path | str) -> "LayoutConfig":
        """Load configuration from TOML file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"No TOML configuration file at path '{path}'")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Create nested configs, falling back to defaults for missing sections
        window_config = WindowConfig(**data.get("window", {}))
        grid_config = GridConfig.from_dict(data.get("grid", {}))
        advanced_config = AdvancedConfig(**data.get("advanced", {}))
        text_config = ColorConfig.from_dict(data.get("text", {}))

        return cls(
            window=window_config,
            grid=grid_config,
            advanced=advanced_config,
            color=text_config,
        )


__all__ = ["WindowConfig", "GridConfig", "LayoutConfig", "AdvancedConfig"]
