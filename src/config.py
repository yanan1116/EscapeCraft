import os

from legent.environment.env_utils import get_default_env_data_path

from log_config import configure_logger

logger = configure_logger(__name__)
logger.info("Initializing the configs......")
logger.debug(f"Default env path: {get_default_env_data_path()}")


#######################
# Environment configs #
#######################

# openai config
API_KEY = ""
BASE_URL = "" # You **cannot** leave it blank even if you are using the official openai api.


# Project configs
__config_path = os.path.abspath(__file__)
PROJECT_PATH = os.path.dirname(__config_path)
__PREFAB_ROOT = os.path.join(PROJECT_PATH, "../prefabs")
PREFAB_DIR = os.path.join(__PREFAB_ROOT, "prefabs")



# Exit configs
EXIT_WALL = "LowPolyInterior2_Wall1_C1_02" # The wall material for the exit wall
# The door material for the exit door. If you want to use your own door prefab, please change the way to calculate the door size in SceneGeneration.py/DefaultSceneGenerator.__get_exit_door()
EXIT_DOOR = "door/door_1.glb"


# Generation configs

# Generate the room nums in one level. Please refer to Procthor for more information.
# This is not the room nums for the MultiRoom Settings!
ROOM_MIN, ROOM_MAX = (1, 1)


# door_size
DOOR_WIDTH = 1.5
DOOR_HEIGHT = 2.5


# box_size
BOX_HEIGHT = 0.2


# Game Configs
GAME_CACHE_DIR = "./game_cache" # The path for saving the records

# Prefab Configs
# You can use your own prefabs here.
PREFABS_USED = {
    "box": {"path": "box/box_1.glb", "height": BOX_HEIGHT},
    "key": {
        "path": "key/key_1.glb",
        "rotation": [90, 0, 0],
        "scale": [0.0005, 0.0005, 0.0005],
    },
    "paper": {"path": "paper/paper_1.glb"},
}


# This is the max distance for interaction. If you want to be strict to the model evaluation, you can set it smaller.
MAX_INTERACTION_DISTANCE = 4


logger.info("All configs loaded.")
