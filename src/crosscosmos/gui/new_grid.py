import logging
from typing_extensions import override

import arcade
import arcade.gui
import arcade.color
import numpy as np
import pyperclip

from crosscosmos.grid import Grid, Cell
from crosscosmos.enums import CellStatus, WordDirection, MoveDirection, GridSymmetry
from crosscosmos.gui.config import LayoutConfig


logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)


A_TO_Z = list(range(arcade.key.A, arcade.key.Z + 1))
ONE_TO_TEN = list(range(arcade.key.KEY_0, arcade.key.KEY_9 + 1))

# Key values
ALL_KEYS = [k for k in dir(arcade.key) if k.isupper() and "MOD_" not in k]
ALL_KEY_VALS = [getattr(arcade.key, k) for k in ALL_KEYS]

ALL_MODS = [k for k in dir(arcade.key) if k.isupper() and "MOD_" in k]
ALL_MODS_VALS = [getattr(arcade.key, k) for k in ALL_MODS]

class CrossCosmosGui(arcade.Window):
    """View demonstrating a layout with square on left and two columns on right."""

    def __init__(self, grid: Grid, config: LayoutConfig):
        super().__init__(config.window.width, config.window.height, config.window.title, resizable=False)
        self.grid = grid
        self.cfg: LayoutConfig = config

        self.ui_manager: arcade.gui.UIManager = arcade.gui.UIManager()
        self.ui_manager.enable()

        self.toggle_black_mode_active: bool = False
        self.grave_down: bool = False
        self.frame_update_count: int = 0
        self.cursor_visible: bool = True
        self.edit_direction: WordDirection = WordDirection.HORIZONTAL
        self.selected_x: int = 0
        self.selected_y: int = 0


        self._init_layout_parameters()
        self._init_data_structures()
        self._setup()

    @property
    def selected_grid_cell(self) -> Cell:
        """Returns the currently selected cell located by the selected x/y coordinates"""
        return self.grid[self.selected_x, self.selected_y]

    @property
    def selected_gui_cell(self) -> arcade.Sprite:
        """Returns the currently selected cell located by the selected x/y coordinates"""
        return self.grid_sprites[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col]

    @override
    def on_draw(self):
        """Render the screen."""
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, self.width, 0, self.height, arcade.color.BLACK)

        # Draw icons
        self.ui_manager.draw()

        # Batch draw the grid sprites
        self.grid_sprite_list.draw()

        # Draw text
        for t in self.text_labels.flatten():
            t.draw()
        for t in self.cell_letters.flatten():
            t.draw()

    @override
    def on_update(self, delta_time: float):
        """Frequent update calls from the grid that are used for a text blinking animation"""
        self.frame_update_count += 1

        cursor_config = self.cfg.grid.cursor
        blick_frequency = cursor_config.blink_frequency
        if self.cursor_visible and self.frame_update_count % blick_frequency == 0:
            # Reset the counter number
            self.frame_update_count = 0

            # Swap cursor color
            if self.text_curser.color == cursor_config.color1:
                self.text_curser.color = cursor_config.color2
            else:
                self.text_curser.color = cursor_config.color1

    @override
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
        logger.info(f"Key Press: {key}")
        logger.info(f"Numbers: {key in ONE_TO_TEN}")
        logger.info(f"Modifiers: {modifiers}")
        logger.info(f"Ctrl: {modifiers & arcade.key.MOD_CTRL}")

        if self._with_black_toggle_modifiers(modifiers):
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
                    self.grid_sprites[cell.gui_row, cell.gui_col].color = self.cfg.color.search_len

        # Copy current word to clipboard
        if key == arcade.key.C and (modifiers & (arcade.key.MOD_CTRL | arcade.key.MOD_COMMAND)):
            active_word_cells = self.grid.full_word_from_cell(
                self.selected_grid_cell.x, self.selected_grid_cell.y, self.edit_direction
            )
            copy_str = str(active_word_cells).replace("-", "?")
            logger.info(f"Copying to clipboard: {copy_str}")
            pyperclip.copy(copy_str)

    @override
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
        logger.info(f"Key Release: {key}")
        logger.info(f"Numbers: {key in ONE_TO_TEN}")
        logger.info(f"Modifiers: {modifiers}")
        logger.info(f"Ctrl: {modifiers & arcade.key.MOD_CTRL}")

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
            self._update_info_section()
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
            self._update_selected_cell(new_val)
            self.cell_letters[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col].text = new_val
            self.update_gui_colors()

        # Move cursor
        if move_dir is not None:
            new_cell = self.grid.get_next_cell(self.selected_x, self.selected_y, move_dir)
            if new_cell.status != CellStatus.BLACK:
                self.selected_x = new_cell.x
                self.selected_y = new_cell.y
            self.update_gui_colors()
            # self._update_info_section()

        self.grid.save()
        self.sync_gui_grid()

    @override
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

        is_highlighted = sprite.color in [self.cfg.color.block_valid_highlight, self.cfg.color.block_invalid_highlight]

        if cell.status == CellStatus.BLACK:
            self.sync_gui_grid()
            return

        # Check validity
        temp_grid = Grid.from_dict(self.grid.to_json())
        temp_grid.set_grid(grid_row, grid_col, None)
        highlight_color = self.cfg.color.block_valid_highlight if temp_grid.is_valid else self.cfg.color.block_invalid_highlight

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

    @override
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
        if self._with_black_toggle_modifiers(modifiers):
            if cell.status != CellStatus.LOCKED:
                self._toggle_black_square(gui_row, gui_col)
                self._draw_answer_numbers()
                if self.cursor_visible and grid_row == self.selected_x and grid_col == self.selected_y:
                    hide_cursor = True

        # Toggle lock
        elif modifiers & arcade.key.MOD_SHIFT:
            if cell.status in [CellStatus.LOCKED, CellStatus.SET]:
                self.grid.toggle_locked(grid_row, grid_col)
                self._update_locked_color(gui_row, gui_col)

        # Normal click
        elif cell.status != CellStatus.BLACK:
            self.selected_x = grid_row
            self.selected_y = grid_col
            # self._update_info_panel()

        if self.selected_grid_cell.status == CellStatus.LOCKED:
            hide_cursor = True

        if hide_cursor:
            self.update_gui_colors(show_cursor=False)
            self._hide_cursor()
        else:
            self.update_gui_colors(show_cursor=True)

        self.grid.save()
        self.sync_gui_grid()


    def _setup(self):
        """Set up the UI layout."""

        self._create_xword_grid_sprites()

        # Main horizontal box (root container) with explicit size
        main_box = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, 1))

        ################################################################################
        # Left Side
        ################################################################################
        left_container = arcade.gui.UIBoxLayout(vertical=True, size_hint=(self.left_side_ratio, 1))
        left_container.with_background(color=self.cfg.color.grid_background)

        grid_info_ratio = (self.cfg.grid.bottom_margin - self.cfg.grid.top_margin) / self.height

        # ==============================================================
        # Crossword Grid
        # ==============================================================
        left_container.add(self._create_xword_grid(size_hint=(1, 1 - grid_info_ratio)))

        # ==============================================================
        # Bottom text labels
        # ==============================================================

        # Left - Bottom (Info)
        info_section_area = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, grid_info_ratio))
        info_section_area.with_background(color=arcade.color.BUBBLE_GUM)

        # ==============================================================
        # Bottom text labels (1) - Location label / Answer combo
        # ==============================================================
        info1 = arcade.gui.UIBoxLayout(vertical=True, size_hint=(0.17, 1))
        info1.with_background(color=self.cfg.color.info_bar_background1)
        self.grid_location_label = arcade.gui.UILabel(size_hint=(1, 0.5), text="(0,0)", font_size=14)
        self.grid_location_label.with_padding(left=self.cfg.grid.left_margin, top=4)

        self.ans_combo_label = arcade.gui.UILabel(size_hint=(1, 0.5), text="14A / 22D", font_size=14)
        self.ans_combo_label.with_padding(top=2, left=self.cfg.grid.left_margin)
        info1.add(self.grid_location_label)
        info1.add(self.ans_combo_label)

        # ==============================================================
        # Bottom text labels (2) - Current entry / length
        # ==============================================================
        info2 = arcade.gui.UIBoxLayout(vertical=True, size_hint=(0.33, 1))
        info2.with_background(color=self.cfg.color.info_bar_background2)
        self.current_value_label = arcade.gui.UILabel(size_hint=(1, 0.5), text='"ASDF??A?BBQPEE??ADFG"', font_size=14)
        self.current_value_label.with_padding(top=4, left=11)

        n_letters_kv, self.n_letters_label = self._create_label_value(
            label_text="Length:",
            label_pct=0.22,
            top_padding=2,
            left_padding=11,
            vertical_pct=0.5,
            default_value_text="14",
        )

        info2.add(self.current_value_label)
        info2.add(n_letters_kv)
        # self.current_value_label.place_text()

        # ==============================================================
        # Bottom text labels (3) - Num Entries, Num Black
        # ==============================================================
        info3 = arcade.gui.UIBoxLayout(vertical=True, size_hint=(0.25, 1))
        # info3.with_background(color=arcade.color.CANDY_PINK)
        info3.with_background(color=self.cfg.color.info_bar_background1)

        entries_kv, self.n_entries_label = self._create_label_value(
            label_text="# Entries:",
            label_pct=0.4,
            top_padding=4,
            left_padding=11,
            vertical_pct=0.5,
            default_value_text="26",
        )
        # entries_kv = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, 0.5))
        # entries_kv.with_padding(top=4, left=11)
        # n_entries_text = arcade.gui.UILabel(size_hint=(1, 0.4), text="# Entries:", font_size=14)
        # self.n_entries_label = arcade.gui.UILabel(size_hint=(1, 0.6), text="24", font_size=14)
        # entries_kv.add(n_entries_text)
        # entries_kv.add(self.n_entries_label)

        blocks_kv, self.n_blocks_label = self._create_label_value(
            label_text="# Blocks:",
            label_pct=0.4,
            top_padding=2,
            left_padding=11,
            vertical_pct=0.5,
            default_value_text="14 (12.0%)",
        )

        info3.add(entries_kv)
        info3.add(blocks_kv)

        # ==============================================================
        # Bottom text labels (4) - idk
        # ==============================================================
        info4 = arcade.gui.UIBoxLayout(vertical=True, size_hint=(0.25, 1))
        # info4.with_background(color=arcade.color.ORANGE_PEEL)
        info4.with_background(color=self.cfg.color.info_bar_background2)

        # self.avg_length_label = arcade.gui.UILabel(size_hint=(1, 0.5), text="Avg. Length: 6.2", font_size=14)
        # self.avg_length_label.with_padding(top=4, left=11)

        avg_length_kv, self.avg_length_label = self._create_label_value(
            label_text="Avg. Length:",
            label_pct=0.55,
            top_padding=4,
            left_padding=11,
            vertical_pct=0.5,
            default_value_text="12.1",
        )
        avg_score_kv, self.avg_score_label = self._create_label_value(
            label_text="Avg. Score:",
            label_pct=0.55,
            top_padding=2,
            left_padding=11,
            vertical_pct=0.5,
            default_value_text="61.2",
        )

        info4.add(avg_length_kv)
        info4.add(avg_score_kv)

        info_section_area.add(info1)
        info_section_area.add(info2)
        info_section_area.add(info3)
        info_section_area.add(info4)

        left_container.add(info_section_area)

        ################################################################################
        # Right Side
        ################################################################################
        right_container = arcade.gui.UIBoxLayout(vertical=False, size_hint=(self.right_side_ratio, 1))

        # Column 1 - subdivided into top/bottom
        right_main_ratio = 0.9
        right_main_container = arcade.gui.UIBoxLayout(vertical=True, size_hint=(right_main_ratio, 1))

        # Column 1 top half
        right_main_top = arcade.gui.UIWidget(size_hint=(1, 0.5))
        right_main_top.with_background(color=arcade.color.LIGHT_GRAY)

        # Column 1 bottom half
        right_main_bottom = arcade.gui.UIWidget(size_hint=(1, 0.5))
        right_main_bottom.with_background(color=arcade.color.GRAY)

        # Column 2 - full height
        side_bar = arcade.gui.UIWidget(size_hint=(1 - right_main_ratio, 1))
        side_bar.with_background(color=arcade.color.DARK_BLUE_GRAY)

        # Build the layout
        right_main_container.add(right_main_top)
        right_main_container.add(right_main_bottom)

        right_container.add(right_main_container)
        right_container.add(side_bar)

        ################################################################################
        # Main GUI
        ################################################################################
        main_box.add(left_container)
        main_box.add(right_container)

        # Create an anchor to position and size the layout
        anchor = arcade.gui.UIAnchorLayout(width=self.width, height=self.height, children=[main_box])

        # Add to UI manager
        self.ui_manager.add(anchor)

        # Syncronize grid data with GUI
        self.sync_gui_grid()

    def _create_label_value(
        self,
        label_text: str,
        label_pct: float = 0.4,
        vertical_pct: float = 0.5,
        top_padding: int = 2,
        left_padding: int = 11,
        default_value_text: str = "",
    ):
        kv_pair = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, vertical_pct))
        kv_pair.with_padding(top=top_padding, left=left_padding)

        text_label = arcade.gui.UILabel(size_hint=(label_pct, 1), text=label_text, font_size=self.cfg.info.font_size)
        value_label = arcade.gui.UILabel(
            size_hint=(1 - label_pct, 1), text=default_value_text, font_size=self.cfg.info.font_size
        )

        kv_pair.add(text_label)
        kv_pair.add(value_label)

        return kv_pair, value_label

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
        x_adj = x - self.cfg.grid.left_margin
        y_adj = y - self.cfg.grid.bottom_margin

        col = int(x_adj // (self.square_size + self.cfg.grid.inner_margin))
        row = int(y_adj // (self.square_size + self.cfg.grid.inner_margin))

        if row < 0 or row >= self.grid.row_count or col < 0 or col >= self.grid.col_count:
            return False, 0, 0

        return True, row, col


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
                grid_sprite.color = self.cfg.color.cell_background
                cell_letter.color = self.cfg.color.normal_text

                match grid_cell.status:
                    case CellStatus.SET:
                        cell_letter.text = grid_cell.value
                    case CellStatus.LOCKED:
                        cell_letter.text = grid_cell.value
                        cell_letter.color = self.cfg.color.locked_text
                    case CellStatus.BLACK:
                        grid_sprite.color = self.cfg.color.blacked_text
                    case CellStatus.EMPTY:
                        cell_letter.text = ""

        self.update_gui_colors()
        self._update_info_section()

    def _init_layout_parameters(self):
        """
        Initialize layout parameters with responsive sizing.

        Calculates grid dimensions, cell sizes, and font sizes based on
        window size and grid dimensions. Reserves space for right panel.
        """

        # Margin sizes
        grid_config = self.cfg.grid
        total_horizontal_margin = grid_config.left_margin + grid_config.right_margin
        total_vertical_margin = grid_config.top_margin + grid_config.bottom_margin

        self.left_side_ratio = (
            self.height - grid_config.bottom_margin + self.cfg.grid.top_margin
        ) / self.width
        # self.left_side_ratio = self.height / self.width
        self.right_side_ratio = 1 - self.left_side_ratio

        # Calculate the withs for each of the sides based on the computed ratios
        self.left_side_width = self.width * self.left_side_ratio
        self.right_panel_width = self.width * self.right_side_ratio

        #################################################################################
        # Calculate grid dimensions
        #################################################################################
        larger_dim = max(self.grid.row_count, self.grid.col_count)
        vertical_inner_margin_sum = (larger_dim - 1) * grid_config.inner_margin

        # Total available width/height
        available_width = self.width - self.right_panel_width - total_horizontal_margin
        available_height = self.height - total_vertical_margin - vertical_inner_margin_sum

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
        Sets up cursor properties and initial editing state."""

        #################################################################################
        # Grid sprites / letters
        #################################################################################
        self.grid_sprite_list = arcade.SpriteList()
        self.grid_sprites = np.empty(self.grid.grid_size, dtype=arcade.Sprite)
        self.text_labels = np.empty(self.grid.grid_size, dtype=arcade.Text)
        self.cell_letters = np.empty(self.grid.grid_size, dtype=arcade.Text)

        #################################################################################
        # Text cursor
        #################################################################################
        cursor_height = int(self.square_size * 0.5)
        cursor_width = max(2, int(self.square_size * 0.05))

        self.text_cursor = arcade.SpriteSolidColor(width=cursor_width, height=cursor_height, color=arcade.color.WHITE)


    def _create_xword_grid(self, **kwargs):

        # Text cursor
        cursor_config = self.cfg.grid.cursor
        text_curser = arcade.SpriteSolidColor(
            width=cursor_config.width,
            height=int(self.square_size * cursor_config.height_factor),
            color=arcade.color.PINK,
        )
        self.text_curser: arcade.SpriteSolidColor = text_curser

        # TODO-white boarder around outside
        xword_grid_area = arcade.gui.UIWidget(**kwargs)
        return xword_grid_area

    def _create_xword_grid_sprites(self):
        """Create sprites for each grid cell.

        Initializes all visual elements for the crossword grid including:
        - Background sprites for each cell
        - Text objects for letters in cells
        - Number labels for crossword clues
        - Stores GUI coordinates in the underlying grid
        """
        grid_config = self.cfg.grid

        for row in range(self.grid.row_count):
            for column in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(row, column)

                # Calculate position: (Outer margin) + (Number of squares in) + (Half square)
                x = column * (self.square_size + grid_config.inner_margin) + self.half_square + grid_config.left_margin
                y = row * (self.square_size + grid_config.inner_margin) + self.half_square + grid_config.bottom_margin

                # Create cell letter text
                if self.grid[grid_row, grid_col].status in [CellStatus.SET, CellStatus.LOCKED]:
                    text = self.grid[grid_row, grid_col].value
                else:
                    text = ""

                self.cell_letters[row, column] = arcade.Text(
                    text=text,
                    x=x,
                    y=y,
                    color=self.cfg.color.normal_text,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.cell_font_size,
                    font_name="Arial",
                    bold=True,
                )

                # Create number label
                number_offset = self.half_square * 0.7
                self.text_labels[row, column] = arcade.Text(
                    text="",
                    x=x - number_offset,
                    y=y + number_offset,
                    color=self.cfg.color.number,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.number_font_size,
                    font_name="Arial",
                )

                # Create cell sprite
                sprite = arcade.SpriteSolidColor(
                    width=self.square_size, height=self.square_size, color=self.cfg.color.cell_background
                )
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store GUI coordinates in grid
                self.grid[grid_row, grid_col].gui_coordinates = (x, y)
                self.grid[grid_row, grid_col].gui_row = row
                self.grid[grid_row, grid_col].gui_col = column

        self.grid_sprite_list.append(self.text_cursor)
        # self.update_gui_colors(show_cursor=True)
        self._draw_answer_numbers()

    def _draw_answer_numbers(self):
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
            self._show_cursor()

        self._reset_colors()

        # Highlight active word
        active_word_cells = self.grid.full_word_from_cell(
            self.selected_grid_cell.x, self.selected_grid_cell.y, self.edit_direction
        )

        for cell in active_word_cells:
            if cell.status == CellStatus.BLACK or not self.grid.is_cell_valid(cell.x, cell.y):
                continue
            elif cell.x == self.selected_grid_cell.x and cell.y == self.selected_grid_cell.y:
                self.grid_sprites[cell.gui_row, cell.gui_col].color = self.cfg.color.selected_cell
            else:
                self.grid_sprites[cell.gui_row, cell.gui_col].color = self.cfg.color.active_word

    def _reset_colors(self):
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
                    self.grid_sprites[gui_row, gui_col].color = self.cfg.color.invalid_cell
                else:
                    self.grid_sprites[gui_row, gui_col].color = self.cfg.color.default_cell

    def _toggle_black_square(self, gui_row: int, gui_col: int):
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

    def _hide_cursor(self):
        """Hide the text cursor.

        Makes cursor invisible by matching its color to the selected
        cell's background color. Used when selecting locked or black cells.
        """
        self.cursor_visible = False
        self.text_cursor.color = self.selected_gui_cell.color

    def _show_cursor(self):
        """Show the text cursor.

        Makes cursor visible by setting it to the primary cursor color.
        The cursor will blink between two colors via the update method.
        """
        self.cursor_visible = True
        self.text_cursor.color = self.cfg.grid.cursor.color1

    def _update_locked_color(self, gui_row: int, gui_col: int):
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
            gui_text_label.color = self.cfg.color.locked_text
        else:
            gui_text_label.color = self.cfg.color.normal_text

    def _with_black_toggle_modifiers(self, modifiers: int) -> bool:
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
        return bool(with_shift and (with_cmd or with_win))

    def _update_selected_cell(self, new_value: str):
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

    def _update_info_section(self):
        active_entry = self.grid.full_word_from_cell(
            self.selected_grid_cell.x, self.selected_grid_cell.y, self.edit_direction
        )
        self.grid_location_label.text = f"({self.selected_grid_cell.x},{self.selected_grid_cell.y})"
        # self.ans_combo_label.text = ""  TODO
        self.current_value_label.text = f'"{active_entry}"'
        self.n_letters_label.text = len(active_entry)
        self.n_entries_label.text = len(self.grid.h_starts) + len(self.grid.v_starts)

        n_blocks = len([c for c in self.grid.grid.flatten() if c.status == CellStatus.BLACK])
        blocks_pct = 100*(n_blocks / len(self.grid.grid.flatten()))
        self.n_blocks_label.text = f"{n_blocks} ({blocks_pct:.1f}%)"

        # avg_length = self.grid.word_lengths()
        # pass

if __name__ == "__main__":
    """Main function to run the application."""
    # grid = Grid((21, 21))
    # "oops_again1.json"
    grid_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/grids/oops_again/oops_again1.json"
    # grid_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/scratch/matiss/monster_floopy_kleeky.json"
    grid_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/scratch/matiss/lantern_monster.json"
    grid = Grid.load(grid_path)

    # config_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/src/crosscosmos/gui/gui_config.toml"
    # config = LayoutConfig.from_toml(config_path)
    config = LayoutConfig()

    # window = arcade.Window(config.window.width, config.window.height, config.window.title, resizable=False)
    layout_view = CrossCosmosGui(grid, config)
    # layout_view._setup()
    # window.show_view(layout_view)
    arcade.run()
