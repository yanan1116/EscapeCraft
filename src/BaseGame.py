import json
import random
import io
from config import *
from log_config import configure_logger, set_log_level
from PIL import Image
import base64

logger = configure_logger(__name__)


class ConbinationLock:
    def __init__(self, id, **kwargs):
        self.id = id
        password = kwargs.get("password", None)
        self.__password = self.__assign_password(**kwargs) if not password else password

    @property
    def password(self):
        return self.__password

    def __call__(self, user_input):
        return self.check_password(user_input)

    def check_password(self, user_input):
        if str(user_input) == self.__password:
            return True
        return False

    def __assign_password(self, **kwargs):
        length = kwargs.get("length", 4)
        password = "".join([str(random.randint(0, 9)) for _ in range(length)])
        return password


class BaseGame:
    def __init__(self, level_data, hint=False, **kwargs):
        with open(level_data, "r", encoding="utf-8") as f:
            self.__ori_data = json.load(f)

        for name, value in kwargs.items():
            setattr(self, name, value)

        logger.info(f"Loading {level_data} as the base game.")

        self.__add_description()

        self.items = self.__format_items()
        self.__format_link()
        self.__assign_password()
        self.puzzle_images = {}

        self.bag = Bag()
        self.clear = False

        self.hint = hint

    @property
    def bag_desc(self):
        return self.bag.get_bag_desc()

    def __add_description(self):
        """Add a brief summary for every item"""

        for item in self.__ori_data["room"]["items"]:
            if item["type"] == "box":
                __description = "A box "

                if item["unlock_method"]:

                    __description += f"seems that can be open with a {item['unlock_method']['type']}."
                    item["locked"] = True

                else:
                    __description += "unlocked."
                    item["locked"] = False

            elif item["type"] == "key":
                __description = "A key seems to open something."

            # elif item["type"] == "paper":
            #     __description = "A paper with some information on it."

            else:
                __description = None

            if __description:
                item["description"] = __description

    def __format_items(self):
        result = {}

        for item in self.__ori_data["room"]["items"]:
            result[item["id"]] = item

        return result

    def __format_link(self):
        for id, item in self.items.items():
            if item["type"] == "box":
                for content in item["contents"]:
                    self.items[content]["putted_in"] = id

            elif item["type"] == "paper":
                for content in item["contents"]:
                    if isinstance(content, str):
                        self.items[content]["carried_on"] = id
                    elif isinstance(content, dict) and content["type"] == "image":
                        # if image puzzle
                        self.items[content["password_id"]]["carried_on"] = id

    def __assign_password(self):
        """Assign a password to the combination lock"""
        for item_type in self.items:
            if "password" in item_type:
                if self.items[item_type]["show"] or hasattr(self, "password"):
                    try:
                        self.items[item_type]["check_func"] = ConbinationLock(
                            item_type, password=self.password
                        )
                        if hasattr(self, "password"):
                            self.items[self.items[item_type]["carried_on"]][
                                "password"
                            ] = self.items[item_type]["check_func"].password

                    except:
                        raise ValueError(f"You must assign a password with show=True!")
                else:
                    self.items[item_type]["check_func"] = ConbinationLock(item_type)
                    self.items[self.items[item_type]["carried_on"]]["password"] = (
                        self.items[item_type]["check_func"].password
                    )

    @property
    def ori_data(self):
        return self.__ori_data

    def open_box(self, box_id):
        if "box" not in box_id:
            raise ValueError(f"{box_id} is not a box!")

        self.items[box_id]["locked"] = False

        desc = "By opening the box, you got:\n"

        for content in self.items[box_id]["contents"]:
            item_got = self.items[content]
            self.bag.add_item(content, item_got)

            desc += self.bag.get_item_desc(content)

        return desc

    def interaction(self, item_id, **kwargs):
        desc = ""
        get_item = False

        if (not item_id in self.items) and (not item_id == "exit"):
            raise ValueError(f"The game don't have the item {item_id}!")

        logger.warning(
            f"The agent is interacting with objects in the scene. The interactable items: {item_id}"
        )
        user_input = kwargs.get("input", None)
        use_item_id = kwargs.get("use_item_id", None)
        read: bool = kwargs.get("read", False)
        if not self.bag.check_item(use_item_id) and use_item_id:
            return (
                f"You don't have the item {use_item_id} in your bag, please try exploring further in the room!",
                None,
            )

        if item_id == "entrance":
            # for multiroom settings
            desc += f"This is where you start the game. You can explore the room by looking around and interacting with items."
        elif item_id == "exit":
            unlock = self.__ori_data["room"]["exit"]
            desc += f"This door seems to be the exit to get out of here, and can be open with a {unlock['type']}. "

            if unlock["type"] == "password":
                if user_input:
                    user_input = str(user_input)
                    if self.items[unlock["unlock_item_id"]]["check_func"](user_input):
                        self.clear = True
                        desc = "You have used the correct password to unlock the door."
                        logger.critical(
                            f"The agent is using the correct password to unlock the door. The game will be cleared ..."
                        )
                    else:
                        desc = f"You use the password {user_input}, but it seems that this password is wrong!"

            elif unlock["type"] in ["key"]:
                if use_item_id == unlock["unlock_item_id"]:
                    desc = f"You have used the item {use_item_id} to unlock the door successfully."
                    logger.critical(
                        f"The agent is trying to use item {use_item_id} to unlock the door (success). The game will be cleared ..."
                    )
                    self.clear = True

                elif use_item_id:
                    desc = f"You use the item {use_item_id}, but it seems to be the wrong key to unlock the door. Please try other items."
                    logger.info(
                        f"The agent is trying to use item {use_item_id} to unlock the door (fail)"
                    )

            elif unlock["type"] == "interact":
                desc = "You found the door to the exit succesfully!"
                logger.critical(
                    f"The agent finds the door and get out succesfully! The game will be cleared ..."
                )
                self.clear = True

            else:
                raise NotImplementedError

        elif "box" in item_id:
            box = self.items[item_id]
            desc += box["description"]
            if box["locked"]:
                if box["unlock_method"]["type"] in ["key"]:

                    if use_item_id == box["unlock_method"]["id"]:
                        desc = f"You have used the item {use_item_id} to unlock this box. {self.open_box(item_id)}"
                    elif use_item_id:
                        desc = f"You use the item {use_item_id}, but it seems to be the wrong key to unlock the box. Please try other items."
                    else:
                        if self.hint:
                            desc = f"You found the box, but cannot open it right now. You need to find a key to the box"
                elif box["unlock_method"]["type"] == "password":
                    if user_input:
                        user_input = str(user_input)
                        if self.items[box["unlock_method"]["id"]]["check_func"](
                            user_input
                        ):
                            desc = f"You have used the correct password to unlock the box. {self.open_box(item_id)}"

                        else:
                            desc = f"You use the password {user_input}, but it seems that this password is wrong!"
                    else:
                        if self.hint:
                            desc = f"You found the box, but cannot open it right now. You need to find the password"
                else:
                    raise NotImplementedError

            else:
                desc = "You have already unlocked this box and got all the items in the box. The box is clear now!"

        elif read:
            if not self.bag.check_item(item_id):
                desc = f"You don't have the item {item_id} in your bag, please try exploring further in the room!"
            else:
                desc = self.bag.get_item_desc(item_id)
                if self.items[item_id]["type"] == "paper":
                    for idx, content in enumerate(self.items[item_id]["contents"]):
                        if isinstance(content, dict):
                            if content["type"] == "story":
                                desc += f"The {idx+1} part of the paper records a story: {content['content']}\n"
                            elif content["type"] == "image":
                                # 图片路径
                                path = content["image_path"]
                                image = Image.open(path)
                                buffered = io.BytesIO()
                                image.save(buffered, format="JPEG")
                                base64_image = base64.b64encode(
                                    buffered.getvalue()
                                ).decode("utf-8")
                                self.puzzle_images[item_id] = content["image_path"]
                                desc += f"The {idx+1} part of the paper records an image with {content['content']} attached: <img src='data:image/jpeg;base64,{base64_image}'></img>\n"

                        elif isinstance(content, str):
                            desc += f"The {str(idx+1)} part of the paper records a string of numbers {str(self.items[item_id]['password'])}.\n"

        else:
            if self.items[item_id]["show"]:
                self.bag.add_item(item_id, self.items[item_id])
                desc = f"You got: {self.bag.get_item_desc(item_id)}"
                get_item = True

        return desc, get_item

    def __call__(self, item_id, **kwargs):
        return self.interaction(item_id, **kwargs)


class Bag:
    """Inventory System"""
    def __init__(self):
        self.items = {}

    def add_item(self, id, item):
        logger.item(f"Agent get the item {id}")
        self.items[id] = item

    def check_item(self, id):

        return self.items.get(id, False)

    def get_item_desc(self, id):
        if not self.check_item(id):
            return f"You can't get the information of item {id} because you hasn't collect it. Please try exploring further in the room!"

        item = self.items[id]
        desc = ""
        if item.get("description", False):
            desc += f"- item_id: {id}, item: {item['type']}, description: {item['description']}\n"

        elif item["type"] == "paper":
            desc += f"- id: {id}, item: paper, description: A paper "
            for content in item["contents"]:
                if isinstance(content, str):
                    desc += f"written a string of numbers {item['password']}.\n"
                else:
                    try:
                        desc += f"written a {content['type']}.\n"
                    except:
                        import pdb

                        pdb.set_trace()

        else:
            raise NotImplementedError

        return desc

    def get_bag_desc(self):

        desc = ""

        for id, item in self.items.items():
            desc += self.get_item_desc(id)

        return desc
