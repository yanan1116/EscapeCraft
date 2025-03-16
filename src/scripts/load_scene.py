import json
import sys
import argparse

sys.path.append("..")

from legent import (
    Environment,
    ResetInfo
)

import logging
from log_config import configure_logger
from utils import format_scene

logger = configure_logger(__name__)

logging.getLogger("PIL").setLevel(logging.WARNING)


def build_scene_with_lights(scene):

    scene["walls"] = scene.get("walls", [])
    scene["lights"] = scene.get("lights", [])
    
    # light_position, you can change it
    light_position = [6.5, 1.6, 3.60]
    light_rotation = [90, 0, 0]
    scene["walls"].append(
        {"position": light_position, "rotation": light_rotation, "size": [0.001, 0.001, 0.001], "material": "Light"}
    )
    scene["lights"].append(
        {
            "name": "PointLight0",
            "lightType": "Point",
            "position": light_position,
            "rotation": light_rotation,
            "useColorTemperature": True,
            "colorTemperature": 5500.0,
            "color": [0.86, 0.75, 0.39],
            "intensity": 10,  # brightness
            "range": 50,
            "shadowType": "Soft",
        }
    )
    
    return scene


parser = argparse.ArgumentParser()
parser.add_argument("--scene_path", type=str, help="scene path to load")
args = parser.parse_args()


scene = format_scene(args.scene_path)

scene = build_scene_with_lights(scene)

# Explore
env = Environment(
    env_path="auto", camera_resolution_width=1024, camera_field_of_view=120, rendering_options={"use_default_light": 0}
)

logger.warning("Please press Q on the keyboard to start/exit the light mode.")
logger.warning("Please press X on the keyboard to start/exit the full-screen mode.")
logger.warning("Please press ESC on the keyboard to release the mouse.")

try:
    obs = env.reset(ResetInfo(scene))
    while True:
        obs = env.step()

finally:
    env.close()