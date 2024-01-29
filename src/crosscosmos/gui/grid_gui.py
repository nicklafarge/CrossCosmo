# Standard
from configparser import ConfigParser
from typing import Tuple

# Third-party
import arcade
import logging
import numpy as np

# Local
import crosscosmos as xc
from crosscosmos.grid import CellStatus, Direction, WordDirection

logger = logging.getLogger("gui")
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

UPDATES_PER_FRAME = 100

# Colors
BACKGROUND_COLOR = arcade.color.BLACK
CELL_BACKGROUND_COLOR = arcade.color.WHITE
TEXT_COLOR = arcade.color.BLACK
CURSER_COLOR_1 = arcade.color.BLACK
CURSER_COLOR_2 = arcade.color.DARK_GRAY
DEFAULT_CELL_COLOR = (80, 80, 80)
BLACKED_CELL_COLOR = arcade.color.BLACK
SELECTED_CELL_COLOR = arcade.color.LIGHT_GRAY
ACTIVE_WORD_CELL_COLOR = arcade.color.GRAY


class CrossCosmosGame(arcade.Window):
    def __init__(self, config_in: ConfigParser, grid_in: xc.grid.Grid):
        super().__init__(config_in.getint('window', 'width'),
                         config_in.getint('window', 'height'),
                         config_in['window']['title'])

        self.grid = grid_in

        # Frame counter
        self.n_frames = 0

        self.inner_margin = config_in.getint('grid', 'inner_margin')
        self.outer_margin = config_in.getint('grid', 'outer_margin')
        total_inner_margin = (grid.row_count - 1) * self.inner_margin
        self.grid_height = self.height - (2 * self.outer_margin) - total_inner_margin
        self.square_size = int(self.grid_height // grid.row_count)

        # Set the background color of the window
        self.background_color = BACKGROUND_COLOR

        # One dimensional list of all sprites in the two-dimensional sprite list
        self.grid_sprite_list = arcade.SpriteList()

        # This will be a two-dimensional grid of sprites to mirror the two
        # dimensional grid of numbers. This points to the SAME sprites that are
        # in grid_sprite_list, just in a 2d manner.
        # self.grid_sprites = []
        self.grid_sprites = np.empty(grid.grid_size, dtype=arcade.Sprite)
        self.grid_sprites2 = np.empty(grid.grid_size, dtype=arcade.Sprite)
        self.text_labels = np.empty(grid.grid_size, dtype=arcade.Text)
        self.cell_letters = np.empty(grid.grid_size, dtype=arcade.Text)

        self.text_curser_blink_frequency = 30
        text_curser = arcade.SpriteSolidColor(2, int(self.square_size * 0.37), arcade.color.WHITE)
        self.text_curser = text_curser
        self.curser_visible = True
        self.horizontal_mode = True

        self.selected_x = 0
        self.selected_y = 0

        # Create a list of solid-color sprites to represent each grid location
        for row in range(grid.row_count):
            for column in range(grid.col_count):
                # Create grid
                x = column * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)
                y = row * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)

                grid_row, grid_col = self.gui_row_col_to_grid_row_col(row, column)

                # Text placeholders
                text = ""
                if self.grid[grid_row, grid_col].status in [CellStatus.SET, CellStatus.LOCKED]:
                    text = self.grid[grid_row, grid_col].value
                cell_letter = arcade.Text(text=text,
                                          start_x=x,
                                          start_y=y,
                                          color=TEXT_COLOR,
                                          anchor_x='center',
                                          anchor_y='center',
                                          font_size=36)
                self.cell_letters[row, column] = cell_letter

                # Cell number labels
                half_square = self.square_size / 2
                t = arcade.Text(text="",
                                start_x=x - half_square * 0.7,
                                start_y=y + half_square * 0.7,
                                color=TEXT_COLOR,
                                anchor_x='center',
                                anchor_y='center',
                                font_size=10)
                self.text_labels[row, column] = t

                # Background
                sprite = arcade.SpriteSolidColor(self.square_size, self.square_size, CELL_BACKGROUND_COLOR)
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store the location in the grid
                self.grid[grid_row, grid_col].gui_coordinates = (x, y)
                self.grid[grid_row, grid_col].gui_row = row
                self.grid[grid_row, grid_col].gui_col = column

        # Curser
        self.grid_sprite_list.append(text_curser)

        self.update_grid()
        self.draw_answer_numbers()

    @property
    def selected_cell(self):
        return self.grid[self.selected_x, self.selected_y]

    def update_selected_cell(self, new_value: str):
        logger.info(f"Updating cell {self.selected_x}, {self.selected_y} to {new_value}")
        self.grid.set_grid(self.selected_x, self.selected_y, new_value)

    def on_draw(self):
        """
        Render the screen.
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

        #

    def on_update(self, delta_time: float):
        self.n_frames += 1

        if self.curser_visible and self.n_frames % self.text_curser_blink_frequency == 0:
            if self.text_curser.color == CURSER_COLOR_1:
                logger.debug("Curser color 1->2")
                self.text_curser.color = CURSER_COLOR_2
            else:
                logger.debug("Curser color 2->1")
                self.text_curser.color = CURSER_COLOR_1

    def draw_answer_numbers(self):
        logger.info("Drawing answer numbers")
        # Draw grid numbers
        for gui_row in range(self.grid.row_count):
            for gui_col in range(self.grid.col_count):
                grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_col)
                cell = self.grid[grid_row, grid_col]
                self.text_labels[gui_row, gui_col].text = "" if not cell.answer_number else str(cell.answer_number)

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        # Currently undefined if modifiers are present (except shift/caps)
        if modifiers and not ((modifiers & arcade.key.MOD_SHIFT) or (modifiers & arcade.key.MOD_CAPSLOCK)):
            return

        if key == arcade.key.TAB and self.curser_visible:
            logger.info("Switching between horizontal/vertical editing")
            self.horizontal_mode = not self.horizontal_mode
            self.update_grid()

        new_val = None
        if key >= arcade.key.A and key <= arcade.key.Z and self.selected_cell.status == CellStatus.EMPTY:
            key_value = chr(key).upper()
            logger.info(f"Key pressed: {key_value}")
            new_val = key_value

        elif (key == arcade.key.DELETE or key == arcade.key.BACKSPACE) and self.selected_cell.status == CellStatus.SET:
            logger.info(f"Backspace pressed")
            new_val = ""

        if new_val is not None:
            self.update_selected_cell(new_val)
            self.cell_letters[self.selected_cell.gui_row, self.selected_cell.gui_col].text = new_val
            self.update_grid()

    def on_mouse_press(self, x_grid: float, y_grid: float, button, modifiers):
        """ Called when the user presses a mouse button.
        """

        # See which row/col was clicked
        success, gui_row, gui_column = self.gui_xy_to_gui_row_col(x_grid, y_grid)
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_column)

        if not success:
            return

        logger.debug(f"Clicked grid row/col: {grid_row}, {grid_col}")

        # Toggle black square
        with_shift = modifiers & arcade.key.MOD_SHIFT
        with_cmd = modifiers & arcade.key.MOD_COMMAND
        with_win = modifiers & arcade.key.MOD_WINDOWS
        if with_shift and (with_cmd or with_win):
            logger.info("Shift+Command+Click")
            self.toggle_black_square(gui_row, gui_column)
            self.selected_x = grid_row
            self.selected_y = grid_col
            self.update_grid()
            if self.curser_visible and grid_row == self.selected_cell.x and grid_col == self.selected_cell.y:
                self.hide_curser()
                self.reset_colors()
            return

        # Do nothing if already black
        elif self.grid[grid_row, grid_col].status == CellStatus.BLACK:
            logger.debug("Clicked on black square")
            self.hide_curser()
            self.reset_colors()

        # Lock / unlock
        elif modifiers & arcade.key.MOD_SHIFT:
            pass

        else:
            self.show_curser()

        # Select square
        self.selected_x = grid_row
        self.selected_y = grid_col
        self.update_grid()

    def toggle_black_square(self, gui_row: int, gui_column: int):
        grid_row, grid_col = self.gui_row_col_to_grid_row_col(gui_row, gui_column)

        grid_cell_is_black = self.grid[grid_row, grid_col].status == CellStatus.BLACK
        gui_is_black = self.grid_sprites[gui_row][gui_column].color == BLACKED_CELL_COLOR

        if grid_cell_is_black != gui_is_black:
            raise RuntimeError("grid/gui black cells have fallen out of sync")

        if grid_cell_is_black:
            self.grid.set_grid(grid_row, grid_col, "")
            self.grid_sprites[gui_row][gui_column].color = DEFAULT_CELL_COLOR
        else:
            self.grid.set_grid(grid_row, grid_col, None)
            self.grid_sprites[gui_row][gui_column].color = BLACKED_CELL_COLOR

        self.cell_letters[gui_row][gui_column].text = ""
        self.draw_answer_numbers()

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
                else:
                    self.grid_sprites[gui_x][gui_y].color = DEFAULT_CELL_COLOR

    def update_grid(self):
        logger.info("Updating grid")
        selected_gui_x, selected_gui_y = self.selected_cell.gui_coordinates

        # Move the curser
        if self.selected_cell.status == CellStatus.EMPTY:
            logger.info("Cursor on left")
            self.text_curser.center_x = selected_gui_x - self.square_size / 4
        elif self.selected_cell.status == CellStatus.SET:
            logger.info("Cursor on right")
            self.text_curser.center_x = selected_gui_x + self.square_size / 4
        self.text_curser.center_y = selected_gui_y
        # self.show_curser()
        self.reset_colors()

        active_direction = WordDirection.HORIZONTAL if self.horizontal_mode else WordDirection.VERTICAL
        active_word_cells = self.grid.full_word_from_cell(self.selected_cell.x, self.selected_cell.y,
                                                          active_direction)
        for cell in active_word_cells:
            if cell.status == CellStatus.BLACK:
                continue
            elif cell.x == self.selected_cell.x and cell.y == self.selected_cell.y:
                self.grid_sprites[cell.gui_row][cell.gui_col].color = SELECTED_CELL_COLOR
            else:
                self.grid_sprites[cell.gui_row][cell.gui_col].color = ACTIVE_WORD_CELL_COLOR

    def gui_row_col_to_grid_row_col(self, gui_row: int, gui_col: int) -> Tuple[int, int]:
        return self.grid.row_count - gui_row - 1, gui_col

    def gui_xy_to_gui_row_col(self, x_grid: float, y_grid: float) -> Tuple[bool, int, int]:
        # Adjust for outer margins
        x = x_grid - self.outer_margin
        y = y_grid - self.outer_margin

        # Convert the clicked mouse position into grid coordinates
        col = int(x // (self.square_size + self.inner_margin))
        row = int(y // (self.square_size + self.inner_margin))

        logger.debug(f"Clicked x,y coordinates: {x}, {y}")
        logger.debug(f"Clicked gui row/col: {row}, {col}")

        # Make sure we are on-grid. It is possible to click in the upper right
        # corner in the margin and go to a grid location that doesn't exist
        if row < 0 or row >= self.grid.row_count or col < 0 or col >= self.grid.col_count:
            # Simply return from this method since nothing needs updating
            logger.debug("Click out of grid range")
            return False, 0, 0

        return True, row, col

    def hide_curser(self):
        logger.info("Hiding curser")

        self.text_curser.color = BLACKED_CELL_COLOR
        self.curser_visible = False

    def show_curser(self):
        logger.info("Showing curser")
        self.curser_visible = True
        self.text_curser.color = CURSER_COLOR_1


# def on_mouse_press(self, x, y, button, modifiers):
#     """
#     Called when the user presses a mouse button.
#     """
#
#     # Ignore if in margins
#     if x < self.outer_margin or x > (self.width - self.outer_margin):
#         return
#
#     if y < self.outer_margin or y > (self.height - self.outer_margin):
#         return
#
#     # Convert the clicked mouse position into grid coordinates
#     column = int((x + self.outer_margin) // (self.square_size + self.inner_margin))
#     row = int((y + self.outer_margin) // (self.square_size + self.inner_margin))
#
#     print(f"Click coordinates: ({x}, {y}). Grid coordinates: ({row}, {column})")
#
#     # Make sure we are on-grid. It is possible to click in the upper right
#     # corner in the margin and go to a grid location that doesn't exist
#     if row >= self.grid.row_count or column >= self.grid.col_count:
#         # Simply return from this method since nothing needs updating
#         return
#
#     # Flip the color of the sprite
#     if self.grid_sprites[row][column].color == arcade.color.WHITE:
#         self.grid_sprites[row][column].color = arcade.color.GREEN
#     else:
#         self.grid_sprites[row][column].color = arcade.color.WHITE


# def main():


if __name__ == "__main__":
    # Parse config file
    config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"
    config = ConfigParser()
    config.read(config_path)

    size = 6, 6
    # size = 14, 14
    lc = xc.corpus.Corpus.from_test()
    grid = xc.grid.Grid(size, lc)

    CrossCosmosGame(config, grid)
    arcade.run()
    # main()
