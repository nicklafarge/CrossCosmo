import logging
from configparser import ConfigParser
from pathlib import Path
import tomllib

import arcade
import arcade.gui
import arcade.gui.widgets.layout
import numpy as np
import pyperclip

import crosscosmos as xc
from crosscosmos.gui.config import LayoutConfig
from crosscosmos.grid import (
    Cell,
    CellStatus,
    GridSymmetry,
    MoveDirection,
    WordDirection,
)
from crosscosmos.gui.image_transform import RGBTransform

logger = logging.getLogger("gui")
logger.setLevel(logging.DEBUG)

# Constants
UPDATES_PER_FRAME = 100
A_TO_Z = list(range(arcade.key.A, arcade.key.Z + 1))
ONE_TO_TEN = list(range(arcade.key.KEY_0, arcade.key.KEY_9 + 1))

# Background colors
BACKGROUND_COLOR = arcade.color.BLACK
CELL_BACKGROUND_COLOR = arcade.color.WHITE

# Text colors
TEXT_COLOR = arcade.color.BLACK
LOCKED_TEXT_COLOR = (0, 153, 255)  # cyan

# Cursor colors
CURSOR_COLOR_1 = arcade.color.BLACK
CURSOR_COLOR_2 = arcade.color.DARK_GRAY

# Cell colors
DEFAULT_CELL_COLOR = (80, 80, 80)  # Dark-ish Gray
INVALID_CELL_COLOR = arcade.color.OLD_BURGUNDY
BLACKED_CELL_COLOR = arcade.color.BLACK
BLACK_VALID_HIGHLIGHT_COLOR = arcade.color.ARMY_GREEN
BLACK_INVALID_HIGHLIGHT_COLOR = arcade.color.OLD_BURGUNDY
SELECTED_CELL_COLOR = arcade.color.LIGHT_GRAY
ACTIVE_WORD_CELL_COLOR = arcade.color.GRAY
SEARCH_LEN_COLOR = arcade.color.DARK_ELECTRIC_BLUE

# Key values
ALL_KEYS = [k for k in dir(arcade.key) if k.isupper() and "MOD_" not in k]
ALL_KEY_VALS = [getattr(arcade.key, k) for k in ALL_KEYS]

ALL_MODS = [k for k in dir(arcade.key) if k.isupper() and "MOD_" in k]
ALL_MODS_VALS = [getattr(arcade.key, k) for k in ALL_MODS]


class CrossCosmosGame(arcade.Window):
    """Main game window for the crossword puzzle creator.

    A professional crossword puzzle creation interface with grid editing,
    automatic solving, and various helper features.

    Attributes:
        grid (xc.grid.Grid): The underlying crossword grid data structure
        frame_update_count (int): Counter for cursor blink animation
        toggle_black_mode_active (bool): Whether black square toggle mode is active
        grave_down (bool): Whether grave key is pressed (modifier for number keys)

        # Layout parameters
        inner_margin (int): Space between grid cells in pixels
        outer_margin (int): Space between grid and window edge in pixels
        right_panel_width (int): Width of the right info panel
        grid_edge_dimension (int): Total size of the grid area
        square_size (int): Size of each grid cell in pixels
        half_square (float): Half of square_size for positioning
        cell_font_size (int): Font size for letters in cells
        number_font_size (int): Font size for cell numbers

        # Data structures
        grid_sprite_list (arcade.SpriteList): All grid sprites for batch drawing
        grid_sprites (np.array): 2D array of cell background sprites
        text_labels (np.array): 2D array of cell number labels
        cell_letters (np.array): 2D array of cell letter displays

        # UI elements
        text_cursor (arcade.SpriteSolidColor): Blinking text cursor
        cursor_visible (bool): Whether cursor is currently visible
        text_cursor_blink_frequency (int): Frames between cursor blinks
        manager (arcade.gui.UIManager): UI manager for buttons/panels
        position_text (arcade.Text): Displays current grid position
        word_info_text (arcade.Text): Displays current word and length
        direction_text (arcade.Text): Displays current edit direction

        # Editing state
        edit_direction (WordDirection): Current editing direction (H/V)
        selected_x (int): Currently selected cell X coordinate
        selected_y (int): Currently selected cell Y coordinate

    Keyboard Controls:
        Letters A-Z: Type letters into empty cells
        Tab: Toggle between horizontal/vertical editing
        Arrow Keys: Navigate the grid
        Space: Move forward in current direction
        Delete/Backspace: Clear current cell and move back

        Shift+Click: Lock/unlock a cell (prevents editing)
        Shift+Cmd/Win+Click: Toggle black square
        Shift+Cmd/Win+Hover: Preview black square placement

        Cmd/Ctrl+C: Copy current word pattern to clipboard (? for blanks)
        Ctrl+[1-9]: Highlight all words of length 1-9
        Grave+Ctrl+[1-9]: Highlight all words of length 11-19

    Mouse Controls:
        Click: Select a cell
        Shift+Click: Lock/unlock the clicked cell
        Shift+Cmd/Win+Click: Toggle black square at clicked position
        Shift+Cmd/Win+Hover: Preview black square validity (green=valid, red=invalid)

    Button Controls:
        Auto Solve: Clear grid and automatically fill with valid words
        Clear Grid: Remove all letters from the grid
        Save Grid: Save current grid state to file

    Visual Indicators:
        - Light gray: Currently selected cell
        - Dark gray: Other cells in current word
        - Cyan text: Locked cells (can't be edited)
        - Black: Black squares (grid separators)
        - Red: Invalid cell configurations
        - Blue: Cells matching searched word length
        - Blinking cursor: Current typing position
    """

    def __init__(self, grid_in: xc.grid.Grid, config: Path | str | dict | None = None):
        """
        Initialize the crossword creator window.

        Parameters
        ----------
        grid_in : xc.grid.Grid
            Pre-initialized crossword grid to edit
        """

        config_path = None
        if isinstance(config, Path) or isinstance(config, str):
            config_path = Path(config)
        elif not config:
            config_path = xc.config_root / "gui_config.toml"
        elif isinstance(config, dict):
            pass
        else:
            raise ValueError(f"Unexpected config input type: {config}")

        if config_path:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

        super().__init__(int(config["window"]["width"]), int(config["window"]["height"]), config["window"]["title"])

        self.grid = grid_in
        self.frame_update_count = 0
        self.toggle_black_mode_active = False
        self.grave_down = False

        # Initialize layout parameters
        self._init_layout_parameters(config)
        self._init_data_structures()
        self._init_gui_elements()
        self._create_grid_sprites()
        self._init_ui_manager()

        # Initial sync and draw
        self.sync_gui_grid()

    def _init_layout_parameters(self, config: dict):
        """
        Initialize layout parameters with responsive sizing.

        Calculates grid dimensions, cell sizes, and font sizes based on
        window size and grid dimensions. Reserves space for right panel.

        Parameters
        ----------
        config : dict
            Configuration settings
        """
        self.inner_margin: int = int(config["grid"]["inner_margin"])
        self.outer_margin: int = int(config["grid"]["outer_margin"])

        # Calculate grid dimensions
        larger_dim = max(self.grid.row_count, self.grid.col_count)
        vertical_inner_margin_sum = (larger_dim - 1) * self.inner_margin

        # Reserve space for right panel (Split 50/50 between the two columns on the right)
        right_panel_width_pct = float(config["grid"]["width_pct"]["right_panel"])
        self.right_panel_width: int = int(self.width * right_panel_width_pct)
        self.right_panel_column_width = self.right_panel_width / 2.0

        #################################################################################
        # Calculate grid dimensions
        #################################################################################
        larger_dim = max(self.grid.row_count, self.grid.col_count)
        vertical_inner_margin_sum = (larger_dim - 1) * self.inner_margin

        # Total available width/height
        available_width = self.width - self.right_panel_width - 2 * self.outer_margin
        available_height = self.height - 2 * self.outer_margin - vertical_inner_margin_sum

        # Use the smaller dimension to ensure square cells
        self.grid_edge_dimension = min(available_width, available_height)
        self.square_size = int(self.grid_edge_dimension // larger_dim)
        self.half_square = self.square_size / 2

        # Recalculate grid dimension based on actual square size
        self.grid_edge_dimension = self.square_size * larger_dim + vertical_inner_margin_sum

        #################################################################################
        # Font size (based on square cell)
        #################################################################################
        self.cell_font_size = max(12, int(self.square_size * 0.4))
        self.number_font_size = max(8, int(self.square_size * 0.2))

    def _init_data_structures(self):
        """Initialize data structures for sprites and text.

        Creates empty numpy arrays for grid sprites, text labels, and cell letters.
        Sets up cursor properties and initial editing state.
        """
        self.grid_sprite_list = arcade.SpriteList()
        self.grid_sprites = np.empty(self.grid.grid_size, dtype=arcade.Sprite)
        self.text_labels = np.empty(self.grid.grid_size, dtype=arcade.Text)
        self.cell_letters = np.empty(self.grid.grid_size, dtype=arcade.Text)

        # Cursor setup
        self.text_cursor_blink_frequency = 30
        self.cursor_visible = True

        # Editing state
        self.edit_direction = WordDirection.HORIZONTAL
        self.selected_x = 0
        self.selected_y = 0

    def _init_gui_elements(self):
        """Initialize GUI elements like cursor.

        Creates the blinking text cursor with appropriate size based on cell dimensions.
        """
        # Create text cursor with appropriate size
        cursor_height = int(self.square_size * 0.5)
        cursor_width = max(2, int(self.square_size * 0.05))

        self.text_cursor = arcade.SpriteSolidColor(width=cursor_width, height=cursor_height, color=arcade.color.WHITE)

    def _create_grid_sprites(self):
        """Create sprites for each grid cell.

        Initializes all visual elements for the crossword grid including:
        - Background sprites for each cell
        - Text objects for letters in cells
        - Number labels for crossword clues
        - Stores GUI coordinates in the underlying grid
        """
        for row in range(self.grid.row_count):
            for column in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(row, column)

                # Calculate position
                x = column * (self.square_size + self.inner_margin) + self.half_square + self.outer_margin
                y = row * (self.square_size + self.inner_margin) + self.half_square + self.outer_margin

                # Create cell letter text
                text = ""
                if self.grid[grid_row, grid_col].status in [CellStatus.SET, CellStatus.LOCKED]:
                    text = self.grid[grid_row, grid_col].value

                cell_letter = arcade.Text(
                    text=text,
                    x=x,
                    y=y,
                    color=TEXT_COLOR,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.cell_font_size,
                    font_name="Arial",
                    bold=True,
                )
                self.cell_letters[row, column] = cell_letter

                # Create number label
                number_offset = self.half_square * 0.7
                t = arcade.Text(
                    text="",
                    x=x - number_offset,
                    y=y + number_offset,
                    color=TEXT_COLOR,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.number_font_size,
                    font_name="Arial",
                )
                self.text_labels[row, column] = t

                # Create cell sprite
                sprite = arcade.SpriteSolidColor(self.square_size, self.square_size, CELL_BACKGROUND_COLOR)
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store GUI coordinates in grid
                self.grid[grid_row, grid_col].gui_coordinates = (x, y)
                self.grid[grid_row, grid_col].gui_row = row
                self.grid[grid_row, grid_col].gui_col = column

        self.grid_sprite_list.append(self.text_cursor)
        self.update_gui_colors(show_cursor=True)
        self.draw_answer_numbers()

    def _init_ui_manager(self):
        """Initialize UI manager and create UI elements.

        Sets up the arcade GUI manager and creates the right panel
        with information display and control buttons.
        """
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        # Create right panel
        self.right_panel1 = self._create_right_panel()
        self.words_panel = self._create_words_panel()

        # Test multiple panels
        self.right_column = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=0,
            size_hint=(0.2, 0.8),
            # children = [self.right_panel1, self.words_panel]
        )
        # self.right_column.add(self.right_panel1)
        # self.right_column.add(self.right_panel2)

        # Position the panel on the right side
        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=self.right_column,
            anchor_x="right",
            anchor_y="center",
            align_x=0,  # Right edge alignment
            align_y=0,  # Center alignment
        )

        self.manager.add(anchor_layout)

    def _create_words_panel(self) -> arcade.gui.UIWidget:
        """
        Create the right panel with info and controls.

        Builds a vertical panel containing:
        - Title header
        - Dynamic text displays for position, word info, and direction
        - Control buttons for auto-solve, clear, and save

        Returns
        -------
        arcade.gui.UIWidget
            UIWidget with dark background containing all panel elements
        """
        from arcade.gui.experimental import UIScrollArea
        from arcade.gui.experimental.scroll_area import UIScrollBar

        content = arcade.gui.UIAnchorLayout(size_hint=(0.5, 1))

        # Create vertical layout for content
        word_list = arcade.gui.UIBoxLayout(vertical=True, size_hint=(1, 0.2), space_between=1)
        for i in range(100):
            button = arcade.gui.UIFlatButton(height=30, size_hint=(1, None), text=f"Button {i}")
            word_list.add(button)

        v_scroll_area = arcade.gui.UIBoxLayout(vertical=False, size_hint=(0.8, 0.8))
        content.add(v_scroll_area, anchor_x="center", anchor_y="center")
        scroll_layout = v_scroll_area.add(UIScrollArea(size_hint=(1, 1)))
        scroll_layout.with_border(color=arcade.uicolor.WHITE_CLOUDS)
        scroll_layout.add(word_list)

        v_scroll_area.add(UIScrollBar(scroll_layout))
        return content

    def _create_right_panel(self) -> arcade.gui.UIWidget:
        """
        Create the right panel with info and controls.

        Builds a vertical panel containing:
        - Title header
        - Dynamic text displays for position, word info, and direction
        - Control buttons for auto-solve, clear, and save

        Returns
        -------
        arcade.gui.UIWidget
            UIWidget with dark background containing all panel elements
        """
        # Create main panel container
        panel_width = self.right_panel_column_width - 20

        # Create vertical layout for content
        panel_content = arcade.gui.UIBoxLayout(vertical=True, space_between=10, size_hint=(0.2, 1))

        # We'll draw these separately using arcade.Text
        panel_content.add(arcade.gui.UISpace(height=25))  # Position label space
        panel_content.add(arcade.gui.UISpace(height=25))  # Word info space
        panel_content.add(arcade.gui.UISpace(height=25))  # Direction label space
        # Add padding to the content
        padded_content = panel_content.with_padding(all=20)

        # Create regular arcade.Text objects for dynamic labels
        # Position them manually in the right panel area
        panel_x = self.width - self.right_panel_width + 20
        base_y = self.height - 40  # Start below title

        panel = arcade.gui.UIGridLayout(
            column_count=1,
            row_count=3,
            align_horizontal="left",
            background_color=arcade.color.DARK_SLATE_GRAY,
            size_hint=(1, 0.2),
        )

        self.position_text = arcade.gui.UILabel(text="Position: (0, 0)", font_size=14)
        self.word_info_text = arcade.gui.UILabel(text="Word: - (0 letters)", font_size=14)
        self.direction_text = arcade.gui.UILabel(text="Direction: Horizontal", font_size=14)

        panel.add(self.position_text)
        panel.add(self.word_info_text)
        panel.add(self.word_info_text)
        return panel
        # Return the panel with background
        # return padded_content.with_background(color=arcade.color.Color(40, 40, 40, 255))

    def _update_info_panel(self):
        """Update the information displayed in the right panel.

        Updates dynamic text displays to show:
        - Current grid position (x, y)
        - Current word pattern with ? for empty cells
        - Word length
        - Current editing direction
        """
        # Update position
        self.position_text.text = f"Position: ({self.selected_x}, {self.selected_y})"

        # Update current word info
        active_word = self.grid.cell_to_entry(self.selected_x, self.selected_y, self.edit_direction)
        word_str = str(active_word).replace("-", "?")
        word_len = len(active_word)
        self.word_info_text.text = f"Word: {word_str} ({word_len} letters)"

        # Update direction
        dir_str = "Horizontal" if self.edit_direction == WordDirection.HORIZONTAL else "Vertical"
        self.direction_text.text = f"Direction: {dir_str}"

    @property
    def selected_grid_cell(self) -> Cell:
        """Returns the currently selected cell from the grid data structure."""
        return self.grid[self.selected_x, self.selected_y]

    @property
    def selected_gui_cell(self) -> arcade.Sprite:
        """Returns the currently selected GUI sprite for visual updates."""
        return self.grid_sprites[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col]

    def on_draw(self):
        """Render the screen.

        Called automatically by arcade to draw each frame. Renders:
        1. Background colors for grid and panel areas
        2. All grid sprites (cells and cursor)
        3. Cell letters and numbers
        4. UI manager elements (buttons)
        5. Dynamic text displays
        """
        self.clear()

        # Draw grid background
        arcade.draw_lrbt_rectangle_filled(
            left=0,
            right=self.grid_edge_dimension + 2 * self.outer_margin,
            bottom=0,
            top=self.height,
            color=(50, 50, 50),
        )

        # Draw right panel background
        arcade.draw_lrbt_rectangle_filled(
            left=self.width - self.right_panel_width, right=self.width, bottom=0, top=self.height, color=(30, 30, 30)
        )

        # Draw sprites
        self.grid_sprite_list.draw()

        # Draw text
        for t in self.text_labels.flatten():
            t.draw()
        for t in self.cell_letters.flatten():
            t.draw()

        # Draw UI
        self.manager.draw()

        # Draw dynamic text labels
        self.position_text.draw()
        self.word_info_text.draw()
        self.direction_text.draw()

    def on_update(self, delta_time: float):
        """
        Update animations.

        Called automatically each frame to update animations.
        Handles cursor blinking by alternating colors.

        Parameters
        ----------
        delta_time : float
            Time elapsed since last frame (unused)
        """
        self.frame_update_count += 1

        if self.cursor_visible and self.frame_update_count % self.text_cursor_blink_frequency == 0:
            self.frame_update_count = 0

            if self.text_cursor.color == CURSOR_COLOR_1:
                self.text_cursor.color = CURSOR_COLOR_2
            else:
                self.text_cursor.color = CURSOR_COLOR_1

    def sync_gui_grid(self):
        """Synchronize GUI with underlying grid data.

        Updates all visual elements to match the current grid state:
        - Cell colors (default, black, invalid)
        - Letter displays
        - Locked cell indicators (cyan text)
        - Clears text from black cells
        """
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                grid_cell = self.grid[grid_row, grid_col]

                cell_letter = self.cell_letters[gui_row, gui_col]
                grid_sprite = self.grid_sprites[gui_row, gui_col]

                # Reset defaults
                grid_sprite.color = DEFAULT_CELL_COLOR
                cell_letter.color = TEXT_COLOR

                match grid_cell.status:
                    case CellStatus.SET:
                        cell_letter.text = grid_cell.value
                    case CellStatus.LOCKED:
                        cell_letter.text = grid_cell.value
                        cell_letter.color = LOCKED_TEXT_COLOR
                    case CellStatus.BLACK:
                        grid_sprite.color = BLACKED_CELL_COLOR
                    case CellStatus.EMPTY:
                        cell_letter.text = ""

        self.update_gui_colors()

    def on_key_press(self, key, modifiers):
        """
        Handle key press events.

        Processes keyboard shortcuts and special key combinations:
        - Shift+Cmd/Win: Activates black square toggle mode
        - Grave key: Modifier for extending number ranges
        - Ctrl+Number: Highlight words of specific length
        - Cmd/Ctrl+C: Copy current word to clipboard

        Parameters
        ----------
        key : int
            Arcade key code
        modifiers : int
            Bit flags for modifier keys (Shift, Ctrl, etc.)
        """
        if self.with_black_toggle_modifiers(modifiers):
            self.toggle_black_mode_active = True

        if key == arcade.key.GRAVE:
            self.grave_down = True
            return

        # Handle number keys with Ctrl for length search
        if key in ONE_TO_TEN and (modifiers & arcade.key.MOD_CTRL):
            value = int(chr(key))
            if self.grave_down:
                value += 10

            logger.info(f"Searching for answers with length = {value}")
            for cell in self.grid.grid.flatten():
                hlen = self.grid.word_len(cell.i, cell.j, WordDirection.HORIZONTAL)
                vlen = self.grid.word_len(cell.i, cell.j, WordDirection.VERTICAL)
                if hlen == value or vlen == value:
                    self.grid_sprites[cell.gui_row, cell.gui_col].color = SEARCH_LEN_COLOR

        # Copy current word to clipboard
        if key == arcade.key.C and (modifiers & (arcade.key.MOD_CTRL | arcade.key.MOD_COMMAND)):
            active_word_cells = self.grid.cell_to_entry(
                self.selected_grid_cell.x, self.selected_grid_cell.y, self.edit_direction
            )
            copy_str = str(active_word_cells).replace("-", "?")
            logger.info(f"Copying to clipboard: {copy_str}")
            pyperclip.copy(copy_str)

    def on_key_release(self, key, modifiers):
        """
        Handle key release events.

        Main keyboard input handler for:
        - Letter input (A-Z) into cells
        - Navigation (arrows, tab)
        - Editing (delete, backspace)
        - Special keys (space, tab)

        Ignores input when Ctrl/Cmd is held to prevent conflicts
        with keyboard shortcuts.

        Parameters
        ----------
        key : int
            Arcade key code
        modifiers : int
            Bit flags for modifier keys
        """
        if key == arcade.key.GRAVE:
            self.grave_down = False

        self.toggle_black_mode_active = False

        # Handle modifiers
        mod_indices = [i for i, v in enumerate(ALL_MODS_VALS) if modifiers & v]
        mod_names = [ALL_MODS[i] for i in mod_indices]

        # Check for Ctrl/Cmd modifiers (excluding when used with special keys)
        has_ctrl_cmd = any(mod in mod_names for mod in ["MOD_CTRL", "MOD_COMMAND", "MOD_WINDOWS"])

        # Tab: switch direction
        if key == arcade.key.TAB and self.cursor_visible:
            self.edit_direction = (
                WordDirection.VERTICAL if self.edit_direction == WordDirection.HORIZONTAL else WordDirection.HORIZONTAL
            )
            self.update_gui_colors()
            self._update_info_panel()
            return

        # If Ctrl/Cmd is held, don't process letter inputs
        if has_ctrl_cmd:
            return

        # Currently undefined if other modifiers are present (except shift/caps)
        if mod_indices and not all(mod in ["MOD_SHIFT", "MOD_CAPSLOCK"] for mod in mod_names):
            logger.info(f"Ignoring input: modifiers are: {mod_names}")
            return

        new_val = None
        move_dir = None

        # Handle letter input
        if key in A_TO_Z and self.selected_grid_cell.status == CellStatus.EMPTY:
            new_val = chr(key).upper()
            move_dir = (
                MoveDirection.FORWARD_HORIZONTAL
                if self.edit_direction == WordDirection.HORIZONTAL
                else MoveDirection.FORWARD_VERTICAL
            )

        # Handle delete/backspace
        elif key in [arcade.key.DELETE, arcade.key.BACKSPACE]:
            if self.selected_grid_cell.status == CellStatus.SET:
                new_val = ""
            move_dir = (
                MoveDirection.BACK_HORIZONTAL
                if self.edit_direction == WordDirection.HORIZONTAL
                else MoveDirection.BACK_VERTICAL
            )

        # Handle navigation
        elif key == arcade.key.SPACE:
            move_dir = (
                MoveDirection.FORWARD_HORIZONTAL
                if self.edit_direction == WordDirection.HORIZONTAL
                else MoveDirection.FORWARD_VERTICAL
            )
        elif key in [arcade.key.LEFT, arcade.key.MOTION_LEFT]:
            move_dir = MoveDirection.BACK_HORIZONTAL
        elif key in [arcade.key.RIGHT, arcade.key.MOTION_RIGHT]:
            move_dir = MoveDirection.FORWARD_HORIZONTAL
        elif key in [arcade.key.UP, arcade.key.MOTION_UP]:
            move_dir = MoveDirection.BACK_VERTICAL
        elif key in [arcade.key.DOWN, arcade.key.MOTION_DOWN]:
            move_dir = MoveDirection.FORWARD_VERTICAL

        # Update cell value
        if new_val is not None:
            self.update_selected_cell(new_val)
            self.cell_letters[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col].text = new_val
            self.update_gui_colors()

        # Move cursor
        if move_dir is not None:
            new_cell = self.grid.get_next_cell(self.selected_x, self.selected_y, move_dir)
            if new_cell.status != CellStatus.BLACK:
                self.selected_x = new_cell.x
                self.selected_y = new_cell.y
            self.update_gui_colors()
            self._update_info_panel()

        self.grid.save()
        self.sync_gui_grid()

    def with_black_toggle_modifiers(self, modifiers: int) -> bool:
        """
        Check if black toggle modifiers are active.

        Black squares are toggled with Shift+Cmd (Mac) or Shift+Win (Windows).

        Parameters
        ----------
        modifiers : int
            Bit flags for active modifier keys

        Returns
        -------
        bool
            True if the correct modifier combination is pressed
        """
        with_shift = modifiers & arcade.key.MOD_SHIFT
        with_cmd = modifiers & arcade.key.MOD_COMMAND
        with_win = modifiers & arcade.key.MOD_WINDOWS
        return with_shift and (with_cmd or with_win)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        """
        Handle mouse motion events.

        When black toggle mode is active (Shift+Cmd/Win held), shows
        preview of black square placement with color coding:
        - Green: Valid placement (maintains valid grid)
        - Red: Invalid placement (would create invalid grid)

        Also handles symmetry preview if grid has symmetry enabled.

        Parameters
        ----------
        x : int
            Mouse x coordinate
        y : int
            Mouse y coordinate
        dx : int
            Change in x (unused)
        dy : int
            Change in y (unused)
        """
        if not self.toggle_black_mode_active:
            return

        on_gui_grid, gui_row, gui_col = self.gui_xy_to_gui_row_col(x, y)
        if not on_gui_grid:
            self.sync_gui_grid()
            return

        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        cell = self.grid[grid_row, grid_col]
        sprite = self.grid_sprites[gui_row, gui_col]

        is_highlighted = sprite.color in [BLACK_VALID_HIGHLIGHT_COLOR, BLACK_INVALID_HIGHLIGHT_COLOR]

        if cell.status == CellStatus.BLACK:
            self.sync_gui_grid()
            return

        # Check validity
        temp_grid = xc.grid.Grid.from_dict(self.grid.to_json())
        temp_grid.set_grid(grid_row, grid_col, None)
        highlight_color = BLACK_VALID_HIGHLIGHT_COLOR if temp_grid.is_valid else BLACK_INVALID_HIGHLIGHT_COLOR

        if not is_highlighted:
            self.sync_gui_grid()
            sprite.color = highlight_color

        # Handle symmetry
        if self.grid.symmetry != GridSymmetry.NONE:
            symm_row, symm_col = self.grid.get_symmetric_index(grid_row, grid_col, self.grid.symmetry)
            symm_cell = self.grid[symm_row, symm_col]
            symm_sprite = self.grid_sprites[symm_cell.gui_row, symm_cell.gui_col]
            if not is_highlighted:
                symm_sprite.color = highlight_color

    def on_mouse_press(self, x: float, y: float, button, modifiers):
        """
        Handle mouse press events.

        Processes different click types:
        - Normal click: Select cell
        - Shift+click: Toggle lock on cell
        - Shift+Cmd/Win+click: Toggle black square

        Updates cursor visibility based on cell type (hidden for
        locked/black cells).

        Parameters
        ----------
        x : float
            Mouse x coordinate
        y : float
            Mouse y coordinate
        button : int
            Mouse button pressed
        modifiers : int
            Active modifier keys
        """
        on_gui_grid, gui_row, gui_col = self.gui_xy_to_gui_row_col(x, y)
        if not on_gui_grid:
            return

        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        cell = self.grid[grid_row, grid_col]
        hide_cursor = False

        # Toggle black square
        if self.with_black_toggle_modifiers(modifiers):
            if cell.status != CellStatus.LOCKED:
                self.toggle_black_square(gui_row, gui_col)
                self.draw_answer_numbers()
                if self.cursor_visible and grid_row == self.selected_x and grid_col == self.selected_y:
                    hide_cursor = True

        # Toggle lock
        elif modifiers & arcade.key.MOD_SHIFT:
            if cell.status in [CellStatus.LOCKED, CellStatus.SET]:
                self.grid.toggle_locked(grid_row, grid_col)
                self.update_locked_color(gui_row, gui_col)

        # Normal click
        elif cell.status != CellStatus.BLACK:
            self.selected_x = grid_row
            self.selected_y = grid_col
            self._update_info_panel()

        if self.selected_grid_cell.status == CellStatus.LOCKED:
            hide_cursor = True

        if hide_cursor:
            self.update_gui_colors(show_cursor=False)
            self.hide_cursor()
        else:
            self.update_gui_colors(show_cursor=True)

        self.grid.save()
        self.sync_gui_grid()

    def update_selected_cell(self, new_value: str):
        """
        Update the currently selected cell value.

        Updates both the underlying grid data and the GUI display.

        Parameters
        ----------
        new_value : str
            New letter value for the cell (empty string to clear)
        """
        logger.info(f"Updating cell {self.selected_x}, {self.selected_y} to {new_value}")
        self.grid.set_grid(self.selected_x, self.selected_y, new_value)

    def update_locked_color(self, gui_row: int, gui_col: int):
        """
        Update color for locked cells.

        Locked cells are displayed with cyan text to indicate they
        cannot be edited.

        Parameters
        ----------
        gui_row : int
            Row index in GUI coordinates
        gui_col : int
            Column index in GUI coordinates
        """
        gui_text_label = self.cell_letters[gui_row, gui_col]
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        cell = self.grid[grid_row, grid_col]

        if cell.status == CellStatus.LOCKED:
            gui_text_label.color = LOCKED_TEXT_COLOR
        else:
            gui_text_label.color = TEXT_COLOR

    def draw_answer_numbers(self):
        """Draw answer numbers on cells.

        Updates the small numbers in the upper-left corner of cells
        that indicate the start of across or down answers. Numbers
        are assigned by the underlying grid logic.
        """
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                cell = self.grid[grid_row, grid_col]
                self.text_labels[gui_row, gui_col].text = str(cell.answer_number) if cell.answer_number else ""

    def toggle_black_square(self, gui_row: int, gui_col: int):
        """
        Toggle a cell between black and normal status.

        Black squares are used to separate words in the crossword.
        Toggles between:
        - Normal cell → Black square
        - Black square → Empty cell

        Parameters
        ----------
        gui_row : int
            Row index in GUI coordinates
        gui_col : int
            Column index in GUI coordinates
        """
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)

        if self.grid[grid_row, grid_col].status == CellStatus.BLACK:
            self.grid.set_grid(grid_row, grid_col, "")
        else:
            self.grid.set_grid(grid_row, grid_col, None)

        self.sync_gui_grid()
        self.cell_letters[gui_row, gui_col].text = ""

    def reset_colors(self):
        """Reset all cell colors to defaults.

        Sets cells to their base colors:
        - Black cells remain black
        - Invalid cells become red
        - All other cells become default gray

        Called before applying selection/word highlighting.
        """
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                cell = self.grid[grid_row, grid_col]

                if cell.status == CellStatus.BLACK:
                    continue
                elif not self.grid.is_cell_valid(cell.x, cell.y):
                    self.grid_sprites[gui_row, gui_col].color = INVALID_CELL_COLOR
                else:
                    self.grid_sprites[gui_row, gui_col].color = DEFAULT_CELL_COLOR

    def update_gui_colors(self, show_cursor=True):
        """
        Update GUI colors and cursor position.

        Refreshes the visual state of the grid:
        - Moves cursor to selected cell
        - Resets all cells to default colors
        - Highlights selected cell (light gray)
        - Highlights current word (dark gray)
        - Shows/hides cursor based on parameter

        Parameters
        ----------
        show_cursor : bool, optional
            Whether to display the text cursor (default True)
        """
        selected_gui_x, selected_gui_y = self.selected_grid_cell.gui_coordinates

        # Position cursor
        if self.selected_grid_cell.status == CellStatus.SET:
            self.text_cursor.center_x = selected_gui_x + self.square_size / 4
        else:
            self.text_cursor.center_x = selected_gui_x - self.square_size / 4
        self.text_cursor.center_y = selected_gui_y

        if show_cursor:
            self.show_cursor()

        self.reset_colors()

        # Highlight active word
        active_word_cells = self.grid.cell_to_entry(
            self.selected_grid_cell.x, self.selected_grid_cell.y, self.edit_direction
        )

        for cell in active_word_cells:
            if cell.status == CellStatus.BLACK or not self.grid.is_cell_valid(cell.x, cell.y):
                continue
            elif cell.x == self.selected_grid_cell.x and cell.y == self.selected_grid_cell.y:
                self.grid_sprites[cell.gui_row, cell.gui_col].color = SELECTED_CELL_COLOR
            else:
                self.grid_sprites[cell.gui_row, cell.gui_col].color = ACTIVE_WORD_CELL_COLOR

    def gui_row_col_to_grid_row_col(self, gui_row: int, gui_col: int) -> tuple[int, int]:
        """
        Convert GUI coordinates to grid coordinates.

        The GUI uses bottom-left origin while the grid uses top-left,
        so rows need to be inverted.

        Parameters
        ----------
        gui_row : int
            Row index in GUI (bottom-up)
        gui_col : int
            Column index in GUI

        Returns
        -------
        tuple[int, int]
            (grid_row, grid_col) in top-down coordinates
        """
        return self.grid.row_count - gui_row - 1, gui_col

    def gui_xy_to_gui_row_col(self, x: float, y: float) -> tuple[bool, int, int]:
        """
        Convert mouse position to grid coordinates.

        Translates pixel coordinates to grid cell indices, accounting
        for margins and cell spacing.

        Parameters
        ----------
        x : float
            Mouse x position in pixels
        y : float
            Mouse y position in pixels

        Returns
        -------
        tuple[bool, int, int]
            (on_grid, row, col) where:
            - on_grid: True if position is within grid bounds
            - row: Grid row index (0 if off-grid)
            - col: Grid column index (0 if off-grid)
        """
        x_adj = x - self.outer_margin
        y_adj = y - self.outer_margin

        col = int(x_adj // (self.square_size + self.inner_margin))
        row = int(y_adj // (self.square_size + self.inner_margin))

        if row < 0 or row >= self.grid.row_count or col < 0 or col >= self.grid.col_count:
            return False, 0, 0

        return True, row, col

    def hide_cursor(self):
        """Hide the text cursor.

        Makes cursor invisible by matching its color to the selected
        cell's background color. Used when selecting locked or black cells.
        """
        self.cursor_visible = False
        self.text_cursor.color = self.selected_gui_cell.color

    def show_cursor(self):
        """Show the text cursor.

        Makes cursor visible by setting it to the primary cursor color.
        The cursor will blink between two colors via the update method.
        """
        self.cursor_visible = True
        self.text_cursor.color = CURSOR_COLOR_1

    def build_button(self, name: str, texture_str: str, dim: float) -> arcade.gui.UITextureButton:
        """
        Build a textured button with hover and click effects.

        Creates a button with visual feedback by lightening the texture
        on hover and click events.

        Parameters
        ----------
        name : str
            Button identifier (unused but kept for compatibility)
        texture_str : str
            Path to button texture image
        dim : float
            Width and height of the button in pixels

        Returns
        -------
        arcade.gui.UITextureButton
            Button with hover and pressed states
        """
        texture = arcade.load_texture(texture_str)

        hover_image = RGBTransform().mix_with([220] * 3, factor=0.40).applied_to(texture.image)
        texture_hover = arcade.Texture(hover_image)

        click_image = RGBTransform().mix_with([220] * 3, factor=0.90).applied_to(texture.image)
        texture_pressed = arcade.Texture(click_image)

        return arcade.gui.UITextureButton(
            texture=texture,
            width=dim,
            height=dim,
            texture_hovered=texture_hover,
            texture_pressed=texture_pressed,
        )


def run_default(grid: xc.grid.Grid, override_config_path=None):
    """
    Run the crossword creator with default configuration.

    Main entry point for the application. Loads configuration,
    builds grid data structures, and launches the GUI.

    Parameters
    ----------
    grid : xc.grid.Grid
        Pre-initialized crossword grid to edit
    override_config_path : str, optional
        Path to custom config file (default None)
    """

    config_path = xc.crosscosmos_root / "gui" / "gui_config.toml"

    if override_config_path:
        config_path = override_config_path

    config = LayoutConfig.from_toml(config_path)
    grid.build_tries()

    # Create and run GUI window
    CrossCosmosGame(config, grid)
    arcade.run()


if __name__ == "__main__":
    # Parse config file
    # config_path = xc.crosscosmos_root / "gui" / "gui_config.toml"
    # config = ConfigParser()
    # config.read(config_path)

    # Load grid
    test_file = Path(xc.crosscosmos_root / "gui" / "test_grid.json")
    xc_grid = xc.grid.Grid.load("/Users/lafarnb1/Projects/GitHub/CrossCosmos/grids/oops_again/oops_again1.json")
    # xc_grid = xc.grid.Grid.load("/Users/nlafarge/Repos/Personal/CrossCosmo/grids/oops_again/oops_again1.json")
    # xc_grid.corpus = xc.corpus.Corpus.from_lafarge()
    # xc_grid.build_tries()

    # Create and run GUI window
    CrossCosmosGame(xc_grid)
    arcade.run()
