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
    parser.add_argument("--max_retry", default=3, type=int, help="max retry times")
    parser.add_argument("--max_allowed_steps", default=20, type=int, help="max allowed steps to finish the task")

    args = parser.parse_args()
    return args


args = parse_args()

if args.hint:
    agent_sys_prompt = PromptTemplate_Hint.SYS_PROMPT
else:
    if args.history_type == "key":
        agent_sys_prompt = PromptTemplate_Base.SYS_PROMPT_KEYONLY
    else:
        agent_sys_prompt = PromptTemplate_Base.SYS_PROMPT

agent = AgentPlayer(
    system_prompt=agent_sys_prompt, model=args.model,
    history_type=args.history_type, max_history=args.max_history,
    max_retry=args.max_retry,
)
scene_path = f"../levels/scene_data/{args.level}/{args.scene_id}.json"
level_data = f"../levels/{args.level}.json"

game = Game(agent, scene_path, level_data, args.level, 
            room_num = args.room_num, scene_id = args.scene_id, hint=args.hint)

game.main(args)
