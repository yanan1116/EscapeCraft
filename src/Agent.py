import os
import io, base64, httpx, copy, time, requests, re, json

from openai import OpenAI,AzureOpenAI
from PIL import Image

from log_config import configure_logger
from config import *
from tokencost import count_message_tokens, count_string_tokens

logger = configure_logger(__name__)


retry_flag = True


def get_answer_img_test(client, model):
    logger.debug(f'tested model: {model}')
    
    image_url_duck = "https://upload.wikimedia.org/wikipedia/commons/d/da/2015_Kaczka_krzy%C5%BCowka_w_wodzie_%28samiec%29.jpg"
    image_url_lion = "https://upload.wikimedia.org/wikipedia/commons/7/77/002_The_lion_king_Snyggve_in_the_Serengeti_National_Park_Photo_by_Giles_Laurent.jpg"

    completion = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "What are the animals in these images?"},
                {"type": "image_url", "image_url": {"url": image_url_duck}},
            ],
        }],
        temperature = 0, max_completion_tokens=20
    )
    assert completion.choices[0].message.content
    print(completion.usage.prompt_tokens)
    print(completion.usage.completion_tokens)


class AgentPlayer:
    def __init__(self, system_prompt, model, max_history=None, max_retry=3, history_type="full"):
        """
        arg:
        :history_type: str, default 'full', choose from 'full', 'max', 'key'
        :max_history: int, default None, if history_type is 'max', max_history must to set to a number
        """

        if history_type == "max":
            assert max_history is not None

        logger.info("Initializing the agent.")
        
        # base params for the game
        self.client = AzureOpenAI(
                        azure_endpoint = os.environ['AZURE_ENDPOINT'],  
                        api_version= "2024-10-01-preview",
                        api_key = os.environ['AZURE_OPENAI_API_KEY_41']
                        )
        self.model = model
        self.max_retry = max_retry
        self.history_type = history_type
        self.max_history = max_history

        # for 'key' history type, when some steps are skipped, there will be a disconsistency between  
        # the current view and the last view sent to the agent
        self.show_tranist_prompt = True if history_type == "key" else False 
        # for 'key' history_type, step 0 is always a key step
        # format: {"key_step": bool, "step_prompt": str, "response": str}
        self.step_meta_info = [{"key_step": True, "step_prompt": "", "response": ""}] # create a placeholder here
        self.last_pos  = 0

        # params for story recovery
        self.notes = []

        self.system_messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
        ]
        self.interactions = []
        self.key_interactions = []

        self.img_str_pattern = r"data:image\/[a-zA-Z]+;base64,([A-Za-z0-9+/=]+)"

        self.prompt_tokens = 0
        self.completion_tokens = 0
        
        get_answer_img_test(self.client, self.model)

    def add_problem(self, problem, image_path=None):
        content = "" if self.model.startswith('phi') else []
        self.interactions.append({"role": "user", "content": content})

        self.__add_problem(problem)
        if image_path:
            self.__add_image(image_path)

    def __add_image(self, image_path):
        image = Image.open(image_path)
        if self.show_tranist_prompt and len(self.step_meta_info) > 2:
            round_id = len(self.step_meta_info) - 1 
            transition_prompt = f'After {round_id} rounds, the view has become:'
            if not self.model.startswith('phi'):
                self.interactions[-1]["content"].append(
                    {
                        "type": "text",
                        "text": transition_prompt,
                    }
                )

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        if self.model.startswith('phi'):
            self.interactions[-1]["content"] = f'<img src="data:image/png;base64,{base64_image}" /> <===>\n' + self.interactions[-1]["content"]
        else:
            self.interactions[-1]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high" if not self.model.startswith("claude") else "auto",
                    },
                }
            )

    def add_response(self, response):
        if self.show_tranist_prompt and len(self.step_meta_info) > 1:
            round_id = len(self.step_meta_info) - 1
            response = f'After {round_id} rounds, you got {response}'

        if self.model.startswith('llama'): 
            self.interactions[-1]['content'].pop(-1) # supports only one image, need to remove past scenes
            content = response
        elif self.model.startswith('phi'):
            self.interactions[-1]['content'] = self.interactions[-1]['content'].split('<===>')[-1]
            content = response
        else:
            content = [{"type": "text", "text": response}]

        self.interactions.append(
                {"role": "assistant", "content": content}
            )

        self.step_meta_info[-1]['response'] = response

    def __add_problem(self, text):
        if not "<img src='data:image/jpeg;base64," in text:
            self.interactions[-1]["content"].append({"type": "text", "text": text})
        else:
            match = re.search(self.img_str_pattern, text)
            if match:
                img_strs = match.group(1)
                logger.debug("found a img str in desc")
                text_split = text.split(f"<img src='data:image/jpeg;base64,{img_strs}'></img>")
                self.interactions[-1]["content"].append({"type": "text", "text": text_split[0]})
                self.interactions[-1]["content"].append(
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img_strs}",
                        "detail": "auto"
                        }}
                )
                self.interactions[-1]["content"].append({"type": "text", "text": text_split[1]})
            else:
                self.interactions[-1]["content"].append({"type": "text", "text": text})

    # def take_down_note(self, message):
    #     retry = 0
    #     tmp_message = copy.deepcopy(message)
    #     tmp_message.append({"role": "user", "content": [{"type": "text", "text": "Take down your current thought on the lock room and how to escape it based on former information. Use word to describe your it not structured format."}]})
        
    #     completion = self.client.chat.completions.create(
    #         model=self.model,
    #         messages=tmp_message,
    #         temperature=0,
    #     )
    #     logger.debug("Note already taken!")
    #     return self.notes.append(completion.choices[0].message.content)

        
    def get_key_interactions(self):
        if self.last_pos == 0:
            self.key_interactions = copy.deepcopy(self.interactions)

        else: 
            if self.step_meta_info[self.last_pos - 1]['key_step']: # check if the last step is a key step, if true, append the response
                self.key_interactions.append(self.interactions[self.last_pos*2 - 1])
            
            if self.step_meta_info[self.last_pos]['key_step']: # check if the current step is a key step, if true, append the prompt
                self.key_interactions.append(self.interactions[self.last_pos * 2])
         
        self.last_pos = len(self.step_meta_info)-1

    def get_interactions(self):
        # history settings
        if self.history_type == 'full':
            message = self.system_messages + self.interactions
        elif self.history_type == 'key':
            self.get_key_interactions()
            if self.max_history:
                message = self.system_messages + self.key_interactions[-2*self.max_history:]
            else:
                message = self.system_messages + self.key_interactions
        elif self.history_type == 'max':
            message = self.system_messages + self.interactions[-self.max_history * 2:]
        else:
            raise NotImplementedError   
        return message

    def ask(self):
        message = self.get_interactions()
            
        retry = 0
        # token_usage = count_message_tokens(message, model="gpt-4-0613")
        token_usage = 0
        logger.debug(f"Trying to get answer from agent. msg length:{len(message)} token usage:{token_usage}")
        # print('message:\n', json.dumps(message))
        while retry < self.max_retry:
            try:             
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=message,
                    temperature=0,
                )
                logger.debug("Got answer from agent!")
                self.prompt_tokens += completion.usage.prompt_tokens
                self.completion_tokens += completion.usage.completion_tokens
                return completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Error occur while getting response from client")
                retry += 1
                continue
            
        logger.error("Error occur continuously before max_retry, aborting...")

    def _save_cur_state(self):
        state = {
            "model": self.model,
            "msg": self.message,
            "key_interactions": self.key_interactions,
            "interactions": self.interactions,
        }
