# Standard
from configparser import ConfigParser

# Third-party
import arcade
import logging
import numpy as np

# Local
import crosscosmos as xc

logger = logging.getLogger("gui")


class CrossCosmosGame(arcade.Window):
    def __init__(self, config: ConfigParser, grid: crosscosmos.grid.Grid):
        super().__init__(config.getint('window', 'width'),
                         config.getint('window', 'height'),
                         config['window']['title'])

        self.grid = grid

        self.inner_margin = config.getint('grid', 'inner_margin')
        self.outer_margin = config.getint('grid', 'outer_margin')
        total_inner_margin = (grid.row_count - 1) * self.inner_margin
        self.grid_height = self.height - (2 * self.outer_margin) - total_inner_margin
        self.square_size = int(self.grid_height // grid.row_count)

        # Set the background color of the window
        self.background_color = arcade.color.BLACK

        # One dimensional list of all sprites in the two-dimensional sprite list
        self.grid_sprite_list = arcade.SpriteList()

        # This will be a two-dimensional grid of sprites to mirror the two
        # dimensional grid of numbers. This points to the SAME sprites that are
        # in grid_sprite_list, just in a 2d manner.
        # self.grid_sprites = []
        self.grid_sprites = np.empty(grid.grid_size, dtype=object)

        # Create a list of solid-color sprites to represent each grid location
        for row in range(grid.row_count):
            for column in range(grid.col_count):
                x = column * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)
                y = row * (self.square_size + self.inner_margin) + (self.square_size / 2 + self.outer_margin)
                sprite = arcade.SpriteSolidColor(self.square_size, self.square_size, arcade.color.WHITE)
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprites[row, column] = sprite
                self.grid_sprite_list.append(sprite)

                # Store the location in the grid
                self.grid.loc = (x, y)
                # self.grid_sprites[row].append(sprite)

    def on_draw(self):
        """
        Render the screen.
        """
        # We should always start by clearing the window pixels
        self.clear()

        # Batch draw the grid sprites
        self.grid_sprite_list.draw()

        # Sandbox
        loc = self.grid[0, 1].loc
        arcade.draw_text("Default Font (Arial)",
                         loc[0],
                         loc[1],
                         arcade.color.BLACK,
                         DEFAULT_FONT_SIZE)

    def on_mouse_press(self, x_grid: float, y_grid: float, button, modifiers):
        """ Called when the user presses a mouse button.
        """

        # Adjust for outer margins
        x = x_grid - self.outer_margin
        y = y_grid - self.outer_margin

        # Convert the clicked mouse position into grid coordinates
        column = int(x // (self.square_size + self.inner_margin))
        row = int(y // (self.square_size + self.inner_margin))

        # Make sure we are on-grid. It is possible to click in the upper right
        # corner in the margin and go to a grid location that doesn't exist
        if row >= self.grid.row_count or column >= self.grid.col_count:
            # Simply return from this method since nothing needs updating
            return

        # Flip the color of the sprite
        if self.grid_sprites[row][column].color == arcade.color.WHITE:
            self.grid_sprites[row][column].color = arcade.color.GREEN
        else:
            self.grid_sprites[row][column].color = arcade.color.WHITE

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


def main():
    # Parse config file
    config_path = xc.crosscosmos_root / "gui" / "gui_config.ini"
    config = ConfigParser()
    config.read(config_path)

    size = 6, 6
    lc = xc.corpus.Corpus.from_test()
    grid = crosscosmos.grid.Grid(size, lc)

    CrossCosmosGame(config, grid)
    arcade.run()


if __name__ == "__main__":
    main()
