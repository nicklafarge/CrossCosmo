from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

import arcade

ColorTuple3 = tuple[int, int, int]
ColorTuple4 = tuple[int, int, int, int]
ColorList = list[int]
ColorInputs = (str | ColorTuple3 | ColorTuple4 | ColorList)

def _get_arcade_color(config_val : ColorInputs) -> arcade.color.Color:
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
        """ Percent of the window that a square occupies. """
        return self.height / self.width

@dataclass(frozen=True)
class GridConfig:
    """Grid layout settings."""
    top_margin: int = 20
    right_margin: int = 20
    left_margin: int = 20
    bottom_margin: int = 60
    inner_margin: int = 2
    grid_border_color: arcade.color.Color = arcade.color.WHITE
    grid_background_color: arcade.color.Color = arcade.color.DIM_GRAY
    cell_background_color: arcade.color.Color = arcade.color.WHITE
    blacked_text_color: arcade.color.Color = arcade.color.BLACK

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "GridConfig":
        """ Initializes from a dictionary, converting colors to tuples"""
        color_vars = ["blacked_text_color", "cell_background_color", "grid_background_color"]
        values = _update_colors(values, color_vars)
        return cls(**values)

@dataclass(frozen=True)
class AdvancedConfig:
    """Advanced behavioral settings."""
    text_cursor_blink_frequency: int = 30

@dataclass(frozen=True)
class TextConfig:
    """Advanced behavioral settings."""
    normal_color: arcade.color.Color = arcade.color.BLACK
    locked_color: arcade.color.Color = (0, 153, 255) # cyan
    number_color: arcade.color.Color = arcade.color.DIM_GRAY

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "TextConfig":
        """ Initializes from a dictionary, converting colors to tuples"""
        values = _update_colors(values, ["normal_color", "locked_color"])
        return cls(**values)

@dataclass(frozen=True)
class LayoutConfig:
    """Complete application configuration."""
    window: WindowConfig = field(default_factory=WindowConfig)
    grid: GridConfig = field(default_factory=GridConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)
    text: TextConfig = field(default_factory=TextConfig)

    @classmethod
    def from_toml(cls, path: Path | str) -> "LayoutConfig":
        """Load configuration from TOML file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"No TOML configuration file at path '{path}'")

        with open(path, 'rb') as f:
            data = tomllib.load(f)

        # Create nested configs, falling back to defaults for missing sections
        window_config = WindowConfig(**data.get('window', {}))
        grid_config = GridConfig.from_dict(data.get('grid', {}))
        advanced_config = AdvancedConfig(**data.get('advanced', {}))
        text_config = TextConfig.from_dict(data.get('text', {}))

        return cls(
            window=window_config,
            grid=grid_config,
            advanced=advanced_config,
            text=text_config,
        )

__all__ = ["WindowConfig", "GridConfig", "LayoutConfig", "AdvancedConfig"]