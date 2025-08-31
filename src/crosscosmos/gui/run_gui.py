"""
Entry point for the CrossCosmos GUI
"""

from configparser import ConfigParser
from importlib import resources

import arcade

# Local
import crosscosmos as xc

# Parse config file
config_path = resources.files / "gui_config.toml"
config = ConfigParser()
config.read(config_path)

# Set up the gui
xc.gui.setup.create_gui(config)

# Begin render section
arcade.start_render()

# Create the grid
# xc.gui.setup.create_grid(config, xc.standards.GridSize.NYT_SUNDAY.value)
# xc.gui.setup.create_grid(config, xc.standards.GridSize.NYT_REGULAR.value)
xc.gui.setup.create_grid(config, (6, 6))

# Finish render section
arcade.finish_render()

arcade.create_text_sprite("A", 25, 25)

# Run the GUI
arcade.run()
