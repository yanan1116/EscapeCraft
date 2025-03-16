import os
import json, re
from copy import deepcopy
import traceback
import time

import jsonschema
from jsonschema import validate
from legent import (
    Environment,
    ResetInfo,
    save_image,
    Action,
)
from legent.action.api import (
    HideObject,
    ObjectInView,
)
from legent.utils.math import vec_xz, distance

from BaseGame import BaseGame
from Agent import AgentPlayer
from prompt_config import *
from utils import *
from log_config import configure_logger, set_log_level

logger = configure_logger(__name__)

set_log_level("debug")

class LegentGame:
    def __init__(self, scene, camera_resolution_width=2048, camera_resolution_height=1024):
        self.scene = scene
        self.env = Environment(
            env_path="auto", 
            camera_resolution_width=camera_resolution_width, 
            camera_field_of_view=120, 
            camera_resolution_height=camera_resolution_height
        )
        self.scene["player"]["prefab"] = "null"
        self.scene["player"]["position"] = [100, 0, 100]
        self.obs = self.env.reset(ResetInfo(self.scene))
        self.__get_interaction_items()

        self.pop_items = []
        self.key_history = []

    def __get_interaction_items(self):
        self.interaction_items = {}
        self.first_interaction_items = {}
        for idx, instance in enumerate(self.scene["instances"]):
            item_type = instance.get("item_type", None)
            if item_type:
                self.interaction_items[instance["item_id"]] = idx
                self.first_interaction_items[idx] = False

    def game_shot(self, step, save_path=None, center_mark=True):
        if not save_path:
            __cache_dir = os.path.join(GAME_CACHE_DIR, "steps")
            if not os.path.exists(__cache_dir):
                os.makedirs(__cache_dir)
        else:
            __cache_dir = os.path.join(save_path)
            
        save_path = os.path.join(__cache_dir, f"{step}.png")

        save_image(self.obs.image, save_path, center_mark=center_mark)

        return save_path

    def step(self, action: Action = None):
        if action:
            self.obs = self.env.step(action)
        else:
            self.obs = self.env.step()

    def stop(self):
        self.env.close()

    def hide(self, id):
        api_calls = [HideObject(id)]
        self.obs = self.env.step(Action(api_calls=api_calls))
        self.interaction_items.pop(self.scene["instances"][id]["item_id"])

    def agent_grab_object_id(self):
        object_ids = []
        object_in_views = []
        for item_id, object_id in self.interaction_items.items():
            self.obs = self.env.step(Action(api_calls=[ObjectInView(object_id)]))
            if self.obs.api_returns["in_view"]:
                object_in_views.append(object_id)
                if (
                    distance(
                        vec_xz(
                            self.obs.game_states["instances"][object_id]["position"]
                        ),
                        vec_xz(self.obs.game_states["agent"]["position"]),
                    )
                    < MAX_INTERACTION_DISTANCE
                ):
                    object_ids.append(object_id)

        return object_ids, object_in_views

    def get_agent_position(self):
        return self.obs.game_states["agent"]["position"]
            

class Game:
    def __init__(
        self,
        agent: AgentPlayer,
        scene_path: str,
        level_data: str,
        level: str,
        room_num: int = 1,
        max_retry=5,
        hint = False,
        record_path = None,
        scene_id = None,
        story_only = False,
        continue_game = False,
        suffix_level = "",
        next_room_id = None,
    ):
        self.agent = agent
        self.level_data = level_data
        self.scene_path = scene_path
        self.scene = format_scene(scene_path)
        if self.scene.get("_password", None):
            self.base_game = BaseGame(level_data, hint=hint, password=self.scene["_password"])
        else:
            self.base_game = BaseGame(level_data, hint=hint)
        self.__load_game()
        self.level = level
        self.room_num = room_num
        self.next_room_id = next_room_id
        
        self.record_path = record_path
        if record_path:
            logger.warning(f"Game start in record mode!")
        
        self.json_pattern = re.compile('```json(?P<jstr>[^(```)]+)```')
        self.max_retry = max_retry

        self.steps = -1
        self.__add_steps()

        if hint:
            self.Prompt = PromptTemplate_Hint
        else:
            self.Prompt = PromptTemplate_Base

        if scene_id is not None:
            if room_num > 1:
                if next_room_id:
                    level = f"{room_num}rooms-{level}-{scene_id}-{next_room_id}"
                else:
                    level = f"{room_num}rooms-{level}-{scene_id}"
            else:
                level = f"{level}-{scene_id}" if not suffix_level else f"{level}_{suffix_level}-{scene_id}"
        self.record_save_path = os.path.join(GAME_CACHE_DIR, level, self.agent.model+"_t_1")
        if not os.path.exists(self.record_save_path):
            os.makedirs(self.record_save_path)
        else:
            self.record_save_path = self.check_dirs(self.record_save_path)

        self.story_only = story_only
        self.continue_game = continue_game

    def __load_game(self):
        if self.agent.model.startswith("claude"):
            self.game = LegentGame(self.scene, camera_resolution_width=1960, camera_resolution_height=980)
        else:
            self.game = LegentGame(self.scene)

    def check_dirs(self, path, i=10):
        _path, idx = path.split('_t_')
        idx = int(idx)
        for _i in range(idx,i):
            path = f"{_path}_t_{_i+1}"
            if os.path.exists(path):
                _path, idx = path.split('_t_')
                idx = int(idx)
            else:
                os.makedirs(path)
                return path
        print('exceed test times!')
        exit(1)

    def __verify_format(self, response):
        if response.get("interactions", None) is not None:
            if response["interactions"] == {}:
                response.pop("interactions")
            else:
                if response["interactions"].get("use_item_id", None) is None:
                    response["interactions"]["use_item_id"] = ""
                if response["interactions"].get("input", None) is None:
                    response["interactions"]["input"] = ""
        if any(value is None for value in response.values()):
            keys = list(response.keys())
            for key in keys:
                if response[key] is None: response.pop(key)
        return response

    def __format_repsonse(self, ori_response):
        try:
            ori_response = ori_response.replace(': False', ': false').replace(': True', ': true') # for phi
            ori_response = ori_response.strip('</Assistant>')
            if "```json" in ori_response:
                json_response = self.json_pattern.search(ori_response)
                if json_response:
                    response = json.loads(json_response.group('jstr').strip())
            elif ":\n\n" in ori_response:
                response = json.loads(ori_response.split(':\n\n')[-1].strip())
            elif "<|assistant|>" in ori_response:
                response = json.loads(ori_response.split('<|assistant|>')[-1].strip())
            else:
                response = json.loads(ori_response.strip("`").strip("json"))
            response = self.__verify_format(response)
            validate(instance=response, schema = self.Prompt.INTERACTIOH_SCHEMA)
            logger.info(f"Step {self.steps}'s interaction is legal!")
            return response
        except jsonschema.exceptions.ValidationError as err:
            if err.message.strip().endswith("greater than the maximum of 180"):
                if response.get("rotate_right", 0) > 180:
                    _right = response["rotate_right"]
                    response.pop("rotate_right")
                    if response.get("rotate_left", None) is None:
                        response["rotate_left"] = _right - 180

                if response.get("rotate_left", 0) > 180:
                    _left = response["rotate_left"]
                    response.pop("rotate_left")
                    if response.get("rotate_right", None) is None:
                        response["rotate_right"] = _left - 180
                
                logger.debug(f" Fix bug for the response from {self.agent.model}: {err.message}")
                logger.info(f"Step {self.steps}'s interaction is corrected and now legal!")
                return response

            logger.error(f"Step {self.steps}'s move is illegal! for {err.message}")
            return False
        except:
            logger.error(
                f"Step {self.steps}'s interaction occurs error! Start re-getting the response!"
            )
            print(ori_response)
            if '```json' in ori_response:
                json_response = self.json_pattern.search(ori_response)
                if json_response:
                    try:
                        response = json.loads(json_response.group('jstr').strip())
                    except:
                        return False
                    validate(instance=response, schema = self.Prompt.INTERACTIOH_SCHEMA)
                    logger.info(f"Step {self.steps}'s interaction is legal!")
                    return response
            return False

    def __add_steps(self):
        self.steps += 1
        self.agent.step_meta_info.append({"key_step":False})

    def get_action(self, response):
        action_list = {}
        desc = ""
        obj_interact = False
        obj_interact_fail = True if "grab" in response or "read" in response else False
        for key in response:
            try:
                if not response[key]:
                    continue
                if key in [
                    "move_forward",
                    "move_right",
                    "rotate_right",
                    "rotate_down",
                    "jump",
                ]:
                    if key == "move_forward":
                        action_list["use_teleport"] = True
                        action_list["teleport_forward"] = response[key]
                    else:
                        action_list[key] = response[key]
                    if not "Successfully moved." in desc:
                            desc += "Successfully moved."

                elif key == "look_at":
                    if response[key][0] == 0.5 and response[key][1] == 0.5:
                        continue
                    action_list["look_x"], action_list["look_y"] = response[key]
                    action_list["use_look_at"] = True
                    if not "View moved." in desc:
                            desc += "View moved."

                elif key == "grab":
                    if response[key]:
                        obj_interact = True
                        logger.warning("The agent try to grab.")
                        logger.debug(f"Rationale of actions: {response['rationale']}")
                        object_ids, object_in_views = self.game.agent_grab_object_id()
                        if object_ids:
                            _desc = None
                            for id, object_id in enumerate(object_ids):
                                _desc, get_item = self.base_game.interaction(
                                    self.scene["instances"][object_id]["item_id"],
                                    **response.get("interactions", {}),
                                )

                                if get_item:
                                    self.game.hide(object_id)

                                if not self.game.first_interaction_items[object_id]:    
                                    self.agent.step_meta_info[-1]['key_step'] = True
                                    self.game.first_interaction_items[object_id] = True

                                desc += f"Interaction triggered {id+1} returns information: {_desc}\n"
                                obj_interact_fail = False
                        elif object_in_views:
                            desc += "You try to interact with some object in the scene, but there seems no response. Please try stepping closer towards the object. If you already step closer but find the object not interactable, you should explore elsewhere in the room."
                        else:
                            desc += "There is no interactable objects in the scene or you are too far away from your target, and your interactive action got no responses."

                elif key == "read":
                    desc, get_item = self.base_game.interaction(
                        response[key], read=True
                    )
                    obj_interact = True
                    if desc:
                        obj_interact_fail = False
                        
                elif key == "rationale":
                    action_list["text"] = response[key]

            except Exception as e:
                logger.warning(
                    f"There exits an error: {str(e)} while processing the key {key}. For the sake of continuity, we will skip this key."
                )
                print(traceback.format_exc())
                continue

        if not self.story_only:        
            print('===>', response)
            print('===>', action_list)  
            print('===>', response.get('rationale', None))   
        return Action(**action_list), desc, obj_interact, obj_interact_fail

    def step(self, response):
        if not self.story_only:
            logger.debug("Taking actions ...")

        action, desc, obj_interact, obj_interact_fail = self.get_action(response)
        self.game.step(action)
        self.__add_steps()

        save_path = self.game.game_shot(self.steps, save_path = self.record_save_path)
        logger.info(f"{self.steps} moved and saved successfully!")

        return desc, save_path, obj_interact, obj_interact_fail

    def replace_base64_with_placeholder(self, text, placeholder="---image---"):
        if not isinstance(text, str):
            raise ValueError("text is not a string")

        pattern = r"(data:image\/[a-zA-Z]+;base64,)([A-Za-z0-9+/=]+)"
        replaced_text = re.sub(pattern, r"\1" + placeholder, text)
        return replaced_text

    def ask_for_action(self, desc, save_path, obj_interact, obj_interact_fail):
        if desc:
            if obj_interact:
                if not obj_interact_fail:
                    print_desc = self.replace_base64_with_placeholder(desc)
                    logger.debug(f"The agent get response: {print_desc}")
                    interaction_desc = f"After the last step of interaction, you find:\n{desc}"
                else:
                    logger.debug(f"obj_interact_fail: {desc}")
                    interaction_desc = f"{desc}"
            else:
                interaction_desc = f"{desc} You did not interact with any objects in the last step."
        else:
            interaction_desc = (
                "The last time your action environment was not responsive."
            )

        bag_desc = (
            self.base_game.bag_desc
            if self.base_game.bag_desc
            else "Nothing in your bag."
        )

        step_prompt = self.Prompt.STEP_PROMPT.format(
            interaction_result=interaction_desc, bag_desc=bag_desc
        )

        self.agent.add_problem(step_prompt, save_path)

        retry = 0
        while retry < self.max_retry:
            ori_response = self.agent.ask()
            if not ori_response is None:
                response = self.__format_repsonse(ori_response)
            else:
                response = None

            if response:
                return response, step_prompt
            else:
                print(ori_response)
                retry += 1
        
        return {}, step_prompt

    def read_note(self):
        return self.agent.notes

    def story_recovery(self):
        logger.info("Start story recovery.")
        desc = self.Prompt.story_prompt

        bag_desc = (
            self.base_game.bag_desc
            if self.base_game.bag_desc
            else "There is notiong in your bag."
        )
        recovery_prompt = desc + bag_desc
        self.agent.add_problem(recovery_prompt)
        story = self.agent.ask()
        if story:
            logger.info("Story recovered successfully.")
            return story
        else:
            logger.error("Story recovered failed.")
            return ""

    def check_new_room_desc(self, desc, escaped_rooms, room_left_to_escape):
        if self.base_game.clear and room_left_to_escape > 1:
            escaped_rooms += 1
            if escaped_rooms == 1: 
                escaped_rooms_str = "1st"
            elif escaped_rooms == 2:
                escaped_rooms_str = "2nd"
            elif escaped_rooms == 3:
                escaped_rooms_str = "3rd"
            else:
                escaped_rooms_str = f"{escaped_rooms_str}th"
            desc = f"You have successfully escaped from the {escaped_rooms} room. You are now entering the next room. The initial scene in the new room is shown in the picture."
            return desc
        return desc 

    def main(self):
        room_left_to_escape, escaped_rooms = self.room_num, 0

        logger.info(f"Start playing the game. There are {room_left_to_escape} rooms.")

        results = []

        save_path = self.game.game_shot(self.steps, save_path = self.record_save_path)
        desc = "The initial scene is shown in the picture."
        obj_interact, obj_interact_fail = False, False

        if self.record_path:
            record_steps = json.load(open(self.record_path, "r", encoding="utf-8"))
            if self.story_only:
                self.agent.interactions = deepcopy(self.agent.system_messages)

        # for multi-room
        level_data_list = []
        scene_path_list = []        
        if room_left_to_escape > 1:
            if self.next_room_id:
                level_data_list = [self.level_data, self.level_data.replace(f"1_1.json", f"1_{self.next_room_id}.json")]
                scene_path_list = [self.scene_path, self.scene_path.replace(f"1_1.json", f"1_{self.next_room_id}.json")]
            else:
                for i in range(2,room_left_to_escape+1):
                    new_level_data = re.sub(r"(\d+)(?=\.json$)", str(i), self.level_data)
                    new_scene_path = re.sub(r"(\d+)(?=\.json$)", str(i), self.scene_path)
                    level_data_list.append(new_level_data)
                    scene_path_list.append(new_scene_path)

        if self.level == "level1":
            max_allowed_steps = 50
        elif self.level == "level2":
            max_allowed_steps = 75
        else:
            max_allowed_steps = 75

        grab_tp = 0

        while not self.base_game.clear:
            if self.record_path:
                time.sleep(1)
                try:
                    response = record_steps[self.steps]["response"]
                except:
                    break
                # step_prompt = record_steps[self.steps]["desc"] if self.story_only else None
                step_prompt = record_steps[self.steps]["desc"]
                _img_path = record_steps[self.steps]["save_path"]
                if self.story_only or self.continue_game:
                    self.agent.add_problem(step_prompt, image_path=_img_path)
                    self.agent.add_response(json.dumps(response))
                    if self.continue_game:
                        self.agent.step_meta_info[-1]['step_prompt'] = step_prompt
                        self.agent.step_meta_info[-1]['response'] = response
                        results.append(
                            {
                                "step": self.steps,
                                "desc": self.replace_base64_with_placeholder(step_prompt),
                                "save_path": _img_path,
                                "response": response,
                                "bag": self.base_game.bag_desc,
                                "used_history": len(self.agent.interactions) // 2
                            }
                        )

                desc, save_path, obj_interact, obj_interact_fail = self.step(response)
                desc = self.check_new_room_desc(desc, escaped_rooms, room_left_to_escape)

                if self.base_game.clear and room_left_to_escape > 1:
                    self.base_game.clear =False
                    room_left_to_escape -= 1
                    tmp_bag = self.base_game.bag
                    self.base_game.clear = False
                    self.game.stop()

                    scene_path = scene_path_list.pop(0)
                    level_data = level_data_list.pop(0)
                    logger.warning(f"In a new scene: {scene_path}\nnew level: {level_data}")
                    self.scene = json.load(open(scene_path))      
                    self.__load_game()
                    self.base_game.bag = tmp_bag

                if self.steps >= len(record_steps):
                    if self.continue_game:
                        self.record_path = None
                    else:
                        break
            else:
                bag_len = len(self.base_game.bag_desc)
                response, step_prompt = self.ask_for_action(desc, save_path, obj_interact, obj_interact_fail)
                self.agent.step_meta_info[-1]['step_prompt'] = step_prompt
                self.agent.step_meta_info[-1]['response'] = response

                self.agent.add_response(json.dumps(response))
                if len(self.base_game.bag_desc) > bag_len:
                    grab_tp += 1
                results.append(
                    {
                        "step": self.steps,
                        "desc": self.replace_base64_with_placeholder(step_prompt),
                        "save_path": save_path,
                        "response": response,
                        "bag": self.base_game.bag_desc,
                        "used_history": len(self.agent.interactions) // 2,
                        "grab_tp": grab_tp
                    }
                )
                if response == {}:
                    logger.info("Retry failed. Proceed to stroy recovery.")
                    with open(os.path.join(self.record_save_path, "records.json"), "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=4)
                    break

                desc, save_path, obj_interact, obj_interact_fail = self.step(response)
                desc = self.check_new_room_desc(desc, escaped_rooms, room_left_to_escape)

                with open(os.path.join(self.record_save_path, "records.json"), "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                if self.steps > max_allowed_steps:
                    logger.info(f'\n\n{self.steps} steps, force exit!!!\n\n')
                    break

                if self.base_game.clear:
                    if room_left_to_escape > 1: 
                        room_left_to_escape -= 1
                        tmp_bag = self.base_game.bag
                        self.base_game.clear = False
                        self.game.stop()

                        scene_path = scene_path_list.pop(0)
                        level_data = level_data_list.pop(0)
                        logger.warning(f"In a new scene: {scene_path}\nnew level: {level_data}")
                        self.scene = json.load(open(scene_path))      
                        self.__load_game()
                        self.base_game.bag = tmp_bag

                    else:
                        break
                
        if not self.record_path:
            if self.base_game.clear:
                results.append({'info': f"Game stop at step {self.steps}. Escaped succesfully!"})
            else:
                results.append({'info': f"Game stop at step {self.steps}. Force exit!"})
            with open(os.path.join(self.record_save_path, "records.json"), "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)

        self.game.stop()  
        if (not self.record_path) or self.story_only or self.continue_game:
            story = self.story_recovery()
            print(story)
            step_wise_note = self.read_note()
            print(step_wise_note)
            story = {
                "story": story,
                "step_wise_note": step_wise_note,
            }
            with open(os.path.join(self.record_save_path, "story.json"), "w", encoding="utf-8") as f:
                json.dump(story, f, ensure_ascii=False, indent=4)



