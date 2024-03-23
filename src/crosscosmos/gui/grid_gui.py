# Standard
from configparser import ConfigParser
from typing import Tuple
from pathlib import Path

# Third-party
import arcade
import arcade.gui
import logging
import numpy as np

# Local
import crosscosmos as xc
from crosscosmos import bot
from crosscosmos.grid import CellStatus, WordDirection, Cell, MoveDirection, GridSymmetry
from crosscosmos.gui.image_transform import RGBTransform

logger = logging.getLogger("gui")
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

UPDATES_PER_FRAME = 100
A_TO_Z = list(range(arcade.key.A, arcade.key.Z + 1))
ONE_TO_TEN = list(range(arcade.key.KEY_0, arcade.key.KEY_9 + 1))

# Background colors
BACKGROUND_COLOR = arcade.color.BLACK
CELL_BACKGROUND_COLOR = arcade.color.WHITE

# Text colors
TEXT_COLOR = arcade.color.BLACK
LOCKED_TEXT_COLOR = (0, 153, 255)  # cyan

# Curser colors
CURSER_COLOR_1 = arcade.color.BLACK
CURSER_COLOR_2 = arcade.color.DARK_GRAY

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
    def __init__(self, config_in: ConfigParser, grid_in: xc.grid.Grid):
        super().__init__(config_in.getint('window', 'width'),
                         config_in.getint('window', 'height'),
                         config_in['window']['title'])

        self.grid = grid_in

        # Frame counter to keep track of blinking curser
        self.frame_update_count = 0

        # For hovering over
        self.toggle_black_mode_active = False

        # For using grave as a modifier
        self.grave_down = False

        # Size computations -------------------------------------------------------------------------------------------#

        # Set GUI layout parameters based on the inputted configuration
        self.inner_margin = config_in.getint('grid', 'inner_margin')  # space between each grid cell
        self.outer_margin = config_in.getint('grid', 'outer_margin')  # space between grid and edge of GUI

        # The sum of all inner margins
        larger_dim = max(self.grid.row_count, self.grid.col_count)
        vertical_inner_margin_sum = (larger_dim - 1) * self.inner_margin

        # The total grid height is 
        #   The height of the GUI (from arcade.Window) -
        #   2 * the outer margin size - 
        #   the sum of all inner margins in the vertical direction
        self.grid_edge_dimension = self.height - (2 * self.outer_margin) - vertical_inner_margin_sum
        self.right_outer_margin = self.width - self.outer_margin - self.grid_edge_dimension
        # The size of each square is the height of the total grid divided by the number of rows (as an integer)
        self.square_size = int(self.grid_edge_dimension // larger_dim)

        # Data values -------------------------------------------------------------------------------------------------#

        # One dimensional list of all sprites in the two-dimensional sprite list
        self.grid_sprite_list = arcade.SpriteList()

        # 2D grid of sprites that mirrors the underlying 2D data structure.
        self.grid_sprites = np.empty(self.grid.grid_size, dtype=arcade.Sprite)

        # 2D grid of text labels that represent the vertical/horizontal crossword numbers
        self.text_labels = np.empty(self.grid.grid_size, dtype=arcade.Text)

        # 2D grid of text labels that represent the string value of each cell
        self.cell_letters = np.empty(self.grid.grid_size, dtype=arcade.Text)

        # GUI Objects -------------------------------------------------------------------------------------------------#

        # Create the text cursor
        self.text_curser_blink_frequency = config_in.getint('advanced', 'text_curser_blink_frequency')
        text_curser = arcade.SpriteSolidColor(2, int(self.square_size * 0.37), arcade.color.WHITE)
        self.text_curser: arcade.SpriteSolidColor = text_curser
        self.curser_visible: bool = True

        # Keep track of if we are editing in the horizontal or vertical directinons
        self.edit_direction: WordDirection = WordDirection.HORIZONTAL

        # Keep track of which square is currently selected
        self.selected_x: int = 0
        self.selected_y: int = 0

        # For readability
        self.half_square = self.square_size / 2

        # Create a list of solid-color sprites to represent each grid location
        for row in range(self.grid.row_count):
            for column in range(self.grid.col_count):

                # Convert from GUI row/col indices to underlying grid row/col indices
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(row, column)

                # Compute GUI (x,y) coordinates where (x,y) is the CENTER of each grid square 
                x = column * (self.square_size + self.inner_margin) + self.half_square + self.outer_margin
                y = row * (self.square_size + self.inner_margin) + self.half_square + self.outer_margin

                # Create text placeholders at (x,y) for SET or LOCKED cells
                text = ""
                if self.grid[grid_row, grid_col].status in [CellStatus.SET, CellStatus.LOCKED]:
                    text = self.grid[grid_row, grid_col].value
                cell_letter = arcade.Text(text=text,
                                          start_x=x,
                                          start_y=y,
                                          color=TEXT_COLOR,
                                          anchor_x='center',
                                          anchor_y='center',
                                          font_size=18)
                self.cell_letters[row, column] = cell_letter

                # Cell number labels
                half_square = self.half_square
                t = arcade.Text(text="",
                                start_x=x - half_square * 0.7,
                                start_y=y + half_square * 0.7,
                                color=TEXT_COLOR,
                                anchor_x='center',
                                anchor_y='center',
                                font_size=10)
                self.text_labels[row, column] = t

                # Add solid color square background to the cell
                sprite = arcade.SpriteSolidColor(self.square_size, self.square_size, CELL_BACKGROUND_COLOR)
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store the gui locations for this cell in the underlying grid object
                self.grid[grid_row, grid_col].gui_coordinates = (x, y)
                self.grid[grid_row, grid_col].gui_row = row
                self.grid[grid_row, grid_col].gui_col = column

        # Create the text cursor object
        self.grid_sprite_list.append(text_curser)

        # Update the cell colors
        self.update_gui_colors(show_cursor=True)

        # Draw answer numbers based on the underlying grid cells
        self.draw_answer_numbers()

        # UI Objects --------------------------------------------------------------------------------------------------#

        # a UIManager to handle the UI.
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        # Create a vertical BoxGroup to align buttons
        self.menu_box = arcade.gui.UIBoxLayout()

        ui_icon_dim = self.right_outer_margin / 2.5
        ui_icon_x = self.outer_margin + self.grid_edge_dimension + self.right_outer_margin / 2 - ui_icon_dim / 2

        # Bot button
        bot_y = ui_icon_dim / 2
        bot_button = self.build_button("bot",
                                       ":resources:images/space_shooter/playerShip1_orange.png",
                                       ui_icon_dim)

        @bot_button.event("on_click")
        def on_click_bot_button(event):
            self.grid.clear()
            bot.solve(self.grid)
            self.sync_gui_grid()
            self.grid.save()

        self.menu_box.add(bot_button.with_space_around(bottom=20))
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="bottom",
                align_x=ui_icon_x,
                align_y=bot_y,
                child=self.menu_box)
        )

        # Clear button
        bot_y = ui_icon_dim / 2
        clear_button = self.build_button("clear",
                                         ":resources:images/tiles/bomb.png",
                                         ui_icon_dim)

        @clear_button.event("on_click")
        def on_click_bot_button(event):
            self.grid.clear()
            self.sync_gui_grid()
            self.grid.save()

        self.menu_box.add(clear_button.with_space_around(bottom=20))
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="left",
                anchor_y="bottom",
                align_x=ui_icon_x,
                align_y=bot_y,
                child=self.menu_box)
        )

        # Sync with grid 
        self.sync_gui_grid()

    @property
    def selected_grid_cell(self) -> Cell:
        """ Returns the currently selected cell located by the selected x/y coordinates
        """
        return self.grid[self.selected_x, self.selected_y]

    @property
    def selected_gui_cell(self) -> arcade.Sprite:
        """ Returns the currently selected cell located by the selected x/y coordinates
        """
        return self.grid_sprites[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col]

    def on_draw(self):
        """ Initial rendering the screen

        1) Clear out existing pixels
        2) Draw all sprites on the grid
        3) Draw text/letters on the grid
        """
        # We should always start by clearing the window pixels
        self.clear()

        # Batch draw the grid sprites
        self.grid_sprite_list.draw()

        # Draw the text labels
        for t in self.text_labels.flatten():
            t.draw()

        # Draw the cell letters labels
        for t in self.cell_letters.flatten():
            t.draw()

        # Draw icons
        self.manager.draw()

    def on_update(self, delta_time: float):
        """ Frequent update calls from the grid that are used for a text blinking animation
        """
        self.frame_update_count += 1

        if self.curser_visible and self.frame_update_count % self.text_curser_blink_frequency == 0:
            # Reset the counter number
            self.frame_update_count = 0

            # Swap cursor color
            if self.text_curser.color == CURSER_COLOR_1:
                self.text_curser.color = CURSER_COLOR_2
            else:
                self.text_curser.color = CURSER_COLOR_1

    def sync_gui_grid(self):
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                grid_cell = self.grid[grid_row, grid_col]

                cell_letter = self.cell_letters[gui_row, gui_col]
                grid_sprite = self.grid_sprites[gui_row, gui_col]

                # Default
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
                    case _:
                        pass

        self.update_gui_colors()

    def on_key_press(self, key, modifiers):
        if self.with_black_toggle_modifiers(modifiers):
            self.toggle_black_mode_active = True

        if key == arcade.key.GRAVE:
            self.grave_down = True
            return

        # Show numbers of some length

        logger.info(f"Key: {key}")
        logger.info(f"Numbers: {key in ONE_TO_TEN}")
        logger.info(f"Ctrl: {modifiers & arcade.key.MOD_CTRL}")
        if key in ONE_TO_TEN and (modifiers & arcade.key.MOD_CTRL):
            value = int(chr(key))
            if self.grave_down:
                value += 10

            logger.info(f"Searching for answers with length = {value}")
            for cell in self.grid.grid.flatten():
                if cell.hlen == value or cell.vlen == value:
                    self.grid_sprites[cell.gui_row, cell.gui_col].color = SEARCH_LEN_COLOR

            logger.info(f"Numbers: {key}")

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        pressed_key_indices = [i for i, k in enumerate(ALL_KEY_VALS) if k == key]
        pressed_key_names = [ALL_KEYS[i] for i in pressed_key_indices]
        logger.info(f"Keys pressed: {', '.join(pressed_key_names)}")

        mod_indices = [i for i, v in enumerate(ALL_MODS_VALS) if modifiers & v]
        mod_names = [ALL_KEYS[i] for i in mod_indices]
        logger.info(f"Modifiers: {mod_names}")

        if key == arcade.key.GRAVE:
            self.grave_down = False

        # No key is held down so no more "hover" behavior for black squares
        self.toggle_black_mode_active = False

        # Currently undefined if modifiers are present (except shift/caps)
        if mod_indices and not ("MOD_SHIFT" in mod_names or 'MOD_CAPSLOCK' in mod_names):
            logger.info(f"Ignoring input: modifiers are: {mod_names}")
            return

        # Tab: rotate between vertical and horizontal editing
        if key == arcade.key.TAB and self.curser_visible:
            logger.debug("Switching between horizontal/vertical editing")

            # Switch horizontal <-> vertical editing
            if self.edit_direction == WordDirection.HORIZONTAL:
                self.edit_direction = WordDirection.VERTICAL
            else:
                self.edit_direction = WordDirection.HORIZONTAL

            # Update the gui
            self.update_gui_colors()

        # Value typed from the keyboard (if applicable)
        new_val = None

        # Move direction (if applicable)
        move_dir = None

        match key:
            case key if key in A_TO_Z:
                if self.selected_grid_cell.status == CellStatus.EMPTY:
                    key_value = chr(key).upper()
                    new_val = key_value
                    move_dir = MoveDirection.FORWARD_HORIZONTAL if self.edit_direction == WordDirection.HORIZONTAL \
                        else MoveDirection.FORWARD_VERTICAL

            case key if key in [arcade.key.DELETE, arcade.key.BACKSPACE]:
                move_dir = MoveDirection.BACK_HORIZONTAL if self.edit_direction == WordDirection.HORIZONTAL \
                    else MoveDirection.BACK_VERTICAL

                if self.selected_grid_cell.status == CellStatus.SET:
                    new_val = ""
                    move_dir = MoveDirection.BACK_HORIZONTAL if self.edit_direction == WordDirection.HORIZONTAL \
                        else MoveDirection.BACK_VERTICAL

            case arcade.key.SPACE:
                move_dir = MoveDirection.FORWARD_HORIZONTAL if self.edit_direction == WordDirection.HORIZONTAL \
                    else MoveDirection.FORWARD_VERTICAL
            case key if key in [arcade.key.MOTION_LEFT, arcade.key.LEFT]:
                logger.info("LEFT")
                move_dir = MoveDirection.BACK_HORIZONTAL
            case key if key in [arcade.key.MOTION_RIGHT, arcade.key.RIGHT]:
                logger.info("RIGHT")
                move_dir = MoveDirection.FORWARD_HORIZONTAL
            case key if key in [arcade.key.MOTION_UP, arcade.key.UP]:
                move_dir = MoveDirection.BACK_VERTICAL
            case key if key in [arcade.key.MOTION_DOWN, arcade.key.DOWN]:
                move_dir = MoveDirection.FORWARD_VERTICAL

        if new_val is not None:
            self.update_selected_cell(new_val)
            self.cell_letters[self.selected_grid_cell.gui_row, self.selected_grid_cell.gui_col].text = new_val
            self.update_gui_colors()

        if move_dir is not None:
            new_cell = self.grid.get_next_cell(self.selected_x, self.selected_y, move_dir)

            # Only update if new_x, new_y are not BLACK (i.e. in the corner black)
            if new_cell.status != CellStatus.BLACK:
                self.selected_x = new_cell.x
                self.selected_y = new_cell.y
            self.update_gui_colors()

        self.grid.save()
        self.sync_gui_grid()

    def with_black_toggle_modifiers(self, modifiers: int):
        with_shift = modifiers & arcade.key.MOD_SHIFT
        with_cmd = modifiers & arcade.key.MOD_COMMAND
        with_win = modifiers & arcade.key.MOD_WINDOWS
        return with_shift and (with_cmd or with_win)

    def on_mouse_motion(self, x_grid: int, y_grid: int, dx: int, dy: int):

        # Only defined currently for when the toggle mode is active
        if not self.toggle_black_mode_active:
            return

        # Get the selected cell/sprite
        on_gui_grid, gui_row, gui_col = self.gui_xy_to_gui_row_col(x_grid, y_grid)
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        cell = self.grid[grid_row, grid_col]
        sprite = self.grid_sprites[gui_row, gui_col]
        is_highlighted = sprite.color in [BLACK_VALID_HIGHLIGHT_COLOR, BLACK_INVALID_HIGHLIGHT_COLOR]

        # Continue if off the grid or on a black cell
        if not on_gui_grid or cell.status == CellStatus.BLACK:
            self.sync_gui_grid()
            return

        # Set the color
        temp_grid = xc.grid.Grid.from_dict(self.grid.to_json())
        temp_grid.set_grid(grid_row, grid_col, None)
        highlight_color = BLACK_VALID_HIGHLIGHT_COLOR if temp_grid.is_valid else BLACK_INVALID_HIGHLIGHT_COLOR
        if not is_highlighted:
            self.sync_gui_grid()
            sprite.color = highlight_color

        # Done here if no symmetry is defined
        if self.grid.symmetry == GridSymmetry.NONE:
            return

        # Get the symmetric cell/sprite
        symm_grid_row, symm_grid_col = self.grid.get_symmetric_index(grid_row, grid_col, self.grid.symmetry)
        symm_cell = self.grid[symm_grid_row, symm_grid_col]
        symm_sprite = self.grid_sprites[symm_cell.gui_row][symm_cell.gui_col]

        # Set the symmetric colr
        if not is_highlighted:
            symm_sprite.color = highlight_color

    def on_mouse_press(self, x_grid: float, y_grid: float, button, modifiers):
        """ Called when the user presses a mouse button.
        """
        # See which row/col was clicked
        on_gui_grid, gui_row, gui_col = self.gui_xy_to_gui_row_col(x_grid, y_grid)

        if not on_gui_grid:
            return

        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        logger.info(f"Clicked [{x_grid},{y_grid}]: gui row/col: [{grid_row},{grid_col}]")
        cell = self.grid[grid_row, grid_col]

        hide_cursor = False

        # Toggle black square
        if self.with_black_toggle_modifiers(modifiers):
            logger.info("Shift+Command+Click")

            # Aren't allowed to black out locked squares
            if cell.status == CellStatus.LOCKED:
                return

            # Switch the selected square default -> black (or vice versa)
            self.toggle_black_square(gui_row, gui_col)

            # Update number entries across the entire grid
            self.draw_answer_numbers()

            # Hide the cursor if the click is [normal -> black] AND [on the current square]
            if self.curser_visible and grid_row == self.selected_grid_cell.x and grid_col == self.selected_grid_cell.y:
                hide_cursor = True

        # Normal click on a black square: Do nothing
        elif self.grid[grid_row, grid_col].status == CellStatus.BLACK:
            logger.debug("Clicked on black square")

        # Shift+ click: Lock / unlock selected square
        elif modifiers & arcade.key.MOD_SHIFT:
            logger.debug(f"Toggling locked status of [{grid_row},{grid_col}]")

            # Only toggle if it is SET or LOCKED
            if self.grid[grid_row, grid_col].status in [CellStatus.LOCKED, CellStatus.SET]:
                self.grid.toggle_locked(grid_row, grid_col)
                self.update_locked_color(gui_row, gui_col)

        # Normal click: Update the selected square
        else:
            self.selected_x = grid_row
            self.selected_y = grid_col

        # Hide the cursor if the cell is locked
        if self.selected_grid_cell.status == CellStatus.LOCKED:
            hide_cursor = True

        # Update the grid colors/numbers
        if hide_cursor:
            self.update_gui_colors(show_cursor=False)
            self.hide_curser()
        else:
            self.update_gui_colors(show_cursor=True)

        self.grid.save()
        self.sync_gui_grid()

    def update_selected_cell(self, new_value: str):
        """ Update the currently selected cell with a new string

        Details:
            Updates in the GUI in addition to the underlying grid
        """
        logger.info(f"Updating cell {self.selected_x}, {self.selected_y} to {new_value}")
        self.grid.set_grid(self.selected_x, self.selected_y, new_value)

    def update_locked_color(self, gui_row: int, gui_col: int):
        # gui_sprite = self.grid_sprites[gui_row, gui_col]
        gui_text_label = self.cell_letters[gui_row, gui_col]

        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
        cell = self.grid[grid_row, grid_col]

        if cell.status == CellStatus.LOCKED:
            logger.debug(f"Setting gui [{gui_row},{gui_col}], grid [{grid_row},{grid_col}] to locked")
            # gui_text_label.color = arcade.color.SAE
            # gui_text_label.color = (255, 0, 153)
            gui_text_label.color = LOCKED_TEXT_COLOR
        else:
            gui_text_label.color = TEXT_COLOR

    def draw_answer_numbers(self):
        """ Draw the cell numbers in the GUI (as applicable)
        """
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                # Convert gui row/col to grid row/col
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                cell = self.grid[grid_row, grid_col]

                # Update the text label based on if the cell has an associated answer number
                self.text_labels[gui_row, gui_col].text = "" if not cell.answer_number else str(cell.answer_number)

    def toggle_black_square(self, gui_row: int, gui_column: int):
        """ Toggle a cell to or from a BLACK status
        
        Args:
            gui_row: Selected row in the gui (int)
            gui_column: selected column in the gui (int)

        """

        # Convert gui row/col to grid row/col
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_column)

        # Determine the status of the selected cell 
        grid_cell_is_black = self.grid[grid_row, grid_col].status == CellStatus.BLACK
        gui_is_black = self.grid_sprites[gui_row][gui_column].color == BLACKED_CELL_COLOR

        # This should never happen, so throw an error
        if grid_cell_is_black != gui_is_black:
            raise RuntimeError("grid/gui black cells have fallen out of sync")

        if grid_cell_is_black:
            # Convert Black -> Default
            self.grid.set_grid(grid_row, grid_col, "")
        else:
            # Convert Default -> Black
            self.grid.set_grid(grid_row, grid_col, None)

        self.sync_gui_grid()
        # Set the text to empty whenever BLACK status is changed
        self.cell_letters[gui_row][gui_column].text = ""

    def reset_colors(self):
        logger.info("Resetting colors on grid")

        # Reset all square colors to default gray
        for gui_x in range(self.grid.row_count):
            for gui_y in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_x, gui_y)
                cell = self.grid[grid_row, grid_col]

                # Do nothing if black
                if cell.status == CellStatus.BLACK:
                    continue
                elif not cell.is_valid:
                    self.grid_sprites[gui_x][gui_y].color = INVALID_CELL_COLOR
                else:
                    self.grid_sprites[gui_x][gui_y].color = DEFAULT_CELL_COLOR

    def update_gui_colors(self, show_cursor=True):
        """ Update the GUI
        
        Updating includes:
            - Moving the cursor to the currently selected cell
            - Optionally showing the cursor
            - Resetting all grid cell colors to their default value
            - Set the currently selected cell to the select color
            - Set active cell colors based on if they're in the current edit direction line
        Args:
            show_cursor: True if the update should display the text cursor
        """
        logger.debug("Updating grid")
        selected_gui_x, selected_gui_y = self.selected_grid_cell.gui_coordinates

        if self.selected_grid_cell.status == CellStatus.SET:
            self.text_curser.center_x = selected_gui_x + self.square_size / 4
        else:
            self.text_curser.center_x = selected_gui_x - self.square_size / 4

        self.text_curser.center_y = selected_gui_y

        # Optionally display the text cursor
        if show_cursor:
            self.show_curser()

        # Reset all cells to default color
        self.reset_colors()

        # Get "active" based on the current edit direction
        active_word_cells = self.grid.full_word_from_cell(self.selected_grid_cell.x,
                                                          self.selected_grid_cell.y,
                                                          self.edit_direction)

        # Update the cell based on its status, and whether it is selected
        for cell in active_word_cells:
            if cell.status == CellStatus.BLACK or not cell.is_valid:
                continue
            elif cell.x == self.selected_grid_cell.x and cell.y == self.selected_grid_cell.y:
                self.grid_sprites[cell.gui_row][cell.gui_col].color = SELECTED_CELL_COLOR
            else:
                self.grid_sprites[cell.gui_row][cell.gui_col].color = ACTIVE_WORD_CELL_COLOR

    def gui_row_col_to_grid_row_col(self, gui_row: int, gui_col: int) -> Tuple[int, int]:
        """ Convert gui row/col to underlying grid row/col
        
        Args:
            gui_row: row index in the gui grid (int)
            gui_col: column index in the gui grid (int)

        Returns:
            Tuple[int, int]: row/column index in the underlying grid data object
        """
        return self.grid.row_count - gui_row - 1, gui_col

    def gui_xy_to_gui_row_col(self, x_grid: float, y_grid: float) -> Tuple[bool, int, int]:
        """ Determine which gui cell corresponds to an (x,y) location in the gui
        
        Args:
            x_grid: x coordinate in the arcade.Window gui (float)
            y_grid: y coordinate in the arcade.Window gui (float)

        Returns:
            Tuple[bool, int, int]:
                1) True if (x,y) is within the grid portion of the gui
                2) row index in the gui grid (int)
                3) column index in the gui grid (int)
        """

        # Adjust for outer margins
        x = x_grid - self.outer_margin
        y = y_grid - self.outer_margin

        # Convert the clicked mouse position into grid coordinates
        col = int(x // (self.square_size + self.inner_margin))
        row = int(y // (self.square_size + self.inner_margin))

        logger.debug(f"Clicked x,y coordinates: {x}, {y} -> gui row/col: {row}, {col}")

        # Make sure we are on-grid. 
        #   - It is possible to click outside the grid margins within the arcade.Window
        if row < 0 or row >= self.grid.row_count or col < 0 or col >= self.grid.col_count:
            # Simply return from this method since nothing needs updating
            logger.debug("Clicked (x,y) coordinate is outside of grid range")
            return False, 0, 0

        return True, row, col

    def hide_curser(self):
        logger.debug("Hiding curser")
        self.curser_visible = False
        self.text_curser.color = self.selected_gui_cell.color

    def show_curser(self):
        logger.debug("Showing curser")
        self.curser_visible = True
        self.text_curser.color = CURSER_COLOR_1

    def build_button(self, name: str, texture_str: str, dim: float) -> arcade.gui.UITextureButton:
        texture = arcade.load_texture(texture_str)

        hover_image = RGBTransform().mix_with([220] * 3, factor=.40).applied_to(texture.image)
        texture_hover = arcade.Texture(f"{name}_hover_texture", hover_image)

        click_image = RGBTransform().mix_with([220] * 3, factor=.90).applied_to(texture.image)
        texture_pressed = arcade.Texture("{name}_click_texture", click_image)

        return arcade.gui.UITextureButton(texture=texture,
                                          width=dim,
                                          height=dim,
                                          texture_hovered=texture_hover,
                                          texture_pressed=texture_pressed)


def run_default(grid: xc.grid.Grid, override_config_path=None):
    config = ConfigParser()

    config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"

    if override_config_path:
        config_path = override_config_path

    config.read(config_path)

    grid.build_tries()

    # Create/run gui window
    CrossCosmosGame(config, grid)
    arcade.run()


if __name__ == "__main__":
    # Parse config file
    config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"
    config = ConfigParser()
    config.read(config_path)

    # Load grid

    # Create grid backend
    # test_file = Path(xc.crosscosmos_project_root / "grids" / "famous_last_words.json")
    test_file = Path(xc.crosscosmos_project_root / "test_grid_88.json")
    # test_file = Path(xc.crosscosmos_project_root / "test_grid_55.json")
    xc_grid = xc.grid.Grid.load(test_file)
    xc_grid.corpus = xc.corpus.Corpus.from_test()
    xc_grid.build_tries()
    # xc_grid = xc.grid.Grid(size, corpus_backend)

    # Create/run gui window
    CrossCosmosGame(config, xc_grid)
    arcade.run()
