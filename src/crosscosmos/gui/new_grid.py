import arcade
import arcade.gui
import arcade.color

import numpy as np

from crosscosmos.grid import Grid
from crosscosmos.enums import CellStatus, WordDirection
from crosscosmos.gui.config import LayoutConfig


class LayoutView(arcade.View):
    """View demonstrating a layout with square on left and two columns on right."""

    def __init__(self, grid: Grid, config: LayoutConfig):
        super().__init__()
        self.grid = grid
        self.config: LayoutConfig = config
        self.ui_manager: arcade.gui.UIManager = arcade.gui.UIManager()

    def setup(self):
        """Set up the UI layout."""
        self.ui_manager.enable()

        self._init_layout_parameters()
        self._init_data_structures()
        self._create_xword_grid_sprites()

        # Main horizontal box (root container) with explicit size
        main_box = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, 1))

        ################################################################################
        # Left Side
        ################################################################################
        left_container = arcade.gui.UIBoxLayout(vertical=True, size_hint=(self.left_side_ratio, 1))
        left_container.with_background(color=self.config.grid.grid_background_color)

        grid_info_ratio = (self.config.grid.bottom_margin - self.config.grid.top_margin) / self.window.height

        # ==============================================================
        # Crossword Grid
        # ==============================================================
        xword_grid_area = arcade.gui.UIWidget(size_hint=(1, 1-grid_info_ratio))
        left_container.add(xword_grid_area)

        # ==============================================================
        # Bottom text labels
        # ==============================================================

        # Left - Bottom (Info)
        info_section_area = arcade.gui.UIBoxLayout(vertical=False, size_hint=(1, grid_info_ratio))
        info_section_area.with_background(color=arcade.color.BUBBLE_GUM)

        self.current_value_label = arcade.gui.UILabel(size_hint=(0.4, 1))
        self.current_value_label.with_background(color=arcade.color.BLUEBERRY)

        self.grid_location_label = arcade.gui.UILabel(size_hint=(0.2, 1))
        self.grid_location_label.with_background(color=arcade.color.BLOND)

        self.n_entries_label = arcade.gui.UILabel(size_hint=(0.2, 1))
        self.n_entries_label.with_background(color=arcade.color.CANDY_PINK)

        self.n_black_label = arcade.gui.UILabel(size_hint=(0.2, 1))
        self.n_black_label.with_background(color=arcade.color.ORANGE_PEEL)

        info_section_area.add(self.current_value_label)
        info_section_area.add(self.grid_location_label)
        info_section_area.add(self.n_entries_label)
        info_section_area.add(self.n_black_label)

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
        side_bar = arcade.gui.UIWidget(size_hint=(1-right_main_ratio, 1))
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
        anchor = arcade.gui.UIAnchorLayout(width=self.window.width, height=self.window.height, children=[main_box])

        # Add to UI manager
        self.ui_manager.add(anchor)

        # Syncronize grid data with GUI
        self.sync_gui_grid()

    def on_draw(self):
        """Render the screen."""
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, self.window.width, 0, self.window.height, arcade.color.BLACK)
        self.ui_manager.draw()
        self.grid_sprite_list.draw()

        # Draw text
        for t in self.text_labels.flatten():
            t.draw()
        for t in self.cell_letters.flatten():
            t.draw()

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
                grid_sprite.color = self.config.grid.cell_background_color
                cell_letter.color = self.config.text.normal_color

                match grid_cell.status:
                    case CellStatus.SET:
                        cell_letter.text = grid_cell.value
                    case CellStatus.LOCKED:
                        cell_letter.text = grid_cell.value
                        cell_letter.color = self.config.text.locked_color
                    case CellStatus.BLACK:
                        grid_sprite.color = self.config.grid.blacked_text_color
                    case CellStatus.EMPTY:
                        cell_letter.text = ""

    def _init_layout_parameters(self):
        """
        Initialize layout parameters with responsive sizing.

        Calculates grid dimensions, cell sizes, and font sizes based on
        window size and grid dimensions. Reserves space for right panel.
        """

        # Margin sizes
        grid_config = self.config.grid
        total_horizontal_margin = grid_config.left_margin + grid_config.right_margin
        total_vertical_margin = grid_config.top_margin + grid_config.bottom_margin

        # self.left_side_ratio = (self.window.height-total_vertical_margin) / (self.window.width-total_horizontal_margin)
        self.left_side_ratio = self.window.height / self.window.width
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

        self.text_cursor = arcade.SpriteSolidColor(
            width=cursor_width,
            height=cursor_height,
            color=arcade.color.WHITE
        )

        #################################################################################
        # Editing state
        #################################################################################
        self.cursor_visible = True
        self.edit_direction = WordDirection.HORIZONTAL
        self.selected_x = 0
        self.selected_y = 0

    def _create_xword_grid_sprites(self):
        """Create sprites for each grid cell.

        Initializes all visual elements for the crossword grid including:
        - Background sprites for each cell
        - Text objects for letters in cells
        - Number labels for crossword clues
        - Stores GUI coordinates in the underlying grid
        """
        grid_config = self.config.grid

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

                cell_letter = arcade.Text(
                    text=text,
                    x=x,
                    y=y,
                    color=self.config.text.normal_color,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.cell_font_size,
                    font_name="Arial",
                    bold=True
                )
                self.cell_letters[row, column] = cell_letter

                # Create number label
                number_offset = self.half_square * 0.7
                t = arcade.Text(
                    text="",
                    x=x - number_offset,
                    y=y + number_offset,
                    color=self.config.text.number_color,
                    anchor_x="center",
                    anchor_y="center",
                    font_size=self.number_font_size,
                    font_name="Arial"
                )
                self.text_labels[row, column] = t

                # Create cell sprite
                sprite = arcade.SpriteSolidColor(
                    width=self.square_size,
                    height=self.square_size,
                    color=self.config.grid.cell_background_color)
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

if __name__ == "__main__":
    """Main function to run the application."""
    # grid = Grid((21, 21))
    # "oops_again1.json"
    grid_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/grids/oops_again/oops_again1.json"
    grid = Grid.load(grid_path)

    config_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/src/crosscosmos/gui/gui_config.toml"
    config = LayoutConfig.from_toml(config_path)

    window = arcade.Window(config.window.width, config.window.height, config.window.title, resizable=False)
    layout_view = LayoutView(grid, config)
    layout_view.setup()
    window.show_view(layout_view)
    arcade.run()
