import argparse

from Game import *
from Agent import *
from prompt_config import *
from config import *
from BaseGame import *


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=str, help="level name")
    parser.add_argument("--model", type=str, help="model name")
    parser.add_argument(
        "--room_num", type=int, default=1, help="the number of rooms in [scene_id]"
    )
    parser.add_argument(
        "--scene_id", type=int, default=1, help="scene_id to load of level [level]"
    )
    parser.add_argument(
        "--record_path", type=str, default=None, help="record path to load"
    )
    parser.add_argument(
        "--history_type",
        default="full",
        type=str,
        help="history type, asserted in full, key, max. If you need to use max_history, please set history_type to max",
    )
    parser.add_argument("--hint", action="store_true", help="whether to use hint")
    parser.add_argument(
        "--max_history", default=None, type=int, help="max history length"
    )
    parser.add_argument("--max_retry", default=5, type=int, help="max retry times")
    args = parser.parse_args()
    return args


args = parse_args()

level = args.level
model = args.model
room_num = args.room_num
scene_id = args.scene_id
history_type = args.history_type
max_history = args.max_history
hint = args.hint

max_retry = args.max_retry

if hint:
    agent_sys_prompt = PromptTemplate_Hint.SYS_PROMPT
else:
    if history_type == "key":
        agent_sys_prompt = PromptTemplate_Base.SYS_PROMPT_KEYONLY
    else:
        agent_sys_prompt = PromptTemplate_Base.SYS_PROMPT

agent = AgentPlayer(
    system_prompt=agent_sys_prompt, model=model,
    history_type=history_type, max_history=max_history,
    max_retry=max_retry,
)
scene_path = f"../levels/scene_data/{level}/{scene_id}.json"
level_data = f"../levels/{level}.json"

if args.record_path is not None:
    game = Game(
        agent, scene_path, level_data, level, 
        room_num = room_num, scene_id = scene_id, hint=hint, 
        record_path=args.record_path
    )

else:
    game = Game(agent, scene_path, level_data, level, 
                room_num = room_num, scene_id = scene_id, hint=hint)

game.main()
