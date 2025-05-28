# How Do Multimodal Large Language Models Handle Complex Multimodal Reasoning? Placing Them in An Extensible Escape Game


<p align="center">
  <a href="https://arxiv.org/abs/2503.10042">
    <img src="https://img.shields.io/badge/arXiv-2503.10042-b31b1b.svg" alt="ArXiv">
  </a>
  <a href="https://thunlp-mt.github.io/EscapeCraft/">
    <img src="https://img.shields.io/badge/Homepage-Website-blue" alt="Homepage">
  </a>
</p>


<p align="center">
<img src="./figures/teaser_git.png" alt="Image">
</p>


## Introduction of the project 
forked from [EscapeCraft](https://github.com/THUNLP-MT/EscapeCraft)(https://arxiv.org/abs/2503.10042), this repo is a modified version which only keeps the success rate oriented part, to make it simple and easy to understand and run. 
Several parts such as the history recovery and scene customization has been removed, for conciseness.
The code has been tested based on vllm and azure openai.

## Installation
Refer to the original repo to install. Some libraries have been updated in this `requirements.txt`



## Run the escape game

you can change the `level`, `scene_id` and `model` to test different task using different models.
all available scenes/tasks are in `levels` folder.
```bash
cd src
python main.py --level level3 --scene_id 3 --model gpt-4.1-mini --history_type full --hint --max_allowed_steps 20
```



## Evaluation
It is recommended to collect results from outside of the `main.py` and calculate the overall performance. 

