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


## Example of a successful escape
<p align="center">
<img src="./figures/example.png" alt="Image">
</p>

## Usage
### Installation
You can use conda to create a new environment and install the required packages:
```bash
git clone https://github.com/THUNLP-MT/EscapeCraft.git
cd EscapeCraft
conda create -n mm-escape python=3.11
conda activate mm-escape
pip install -r requirements.txt
```

Then you should download the legent client and env data from [hugging face](https://huggingface.co/LEGENT/LEGENT-environment-Alpha/tree/main) or [Tsinghua Cloud](https://cloud.tsinghua.edu.cn/d/9976c807e6e04e069377/). After downloading, extract and unzip the file to create the following file structure:

```bash
src/
└── .legent/
    └── env/
        ├── client
        │   └── LEGENT-<platform>-<version>
        └── env_data/
            └── env_data-<version>
```
If you have any problem, please refer to [LEGENT](https://docs.legent.ai/documentation/getting_started/installation/).

### Configs
Our EscapeCraft is extensible and can be customized simply by changing the configs in `src/config.py`. All the configs are commented and you can easily modify them to your needs.

### Levels
The levels we provide are in `levels/`. You can refer to the structure of our json file and the way we generate the level proposed in our paper to generate your own level data, which can make the game more challenging and complex.

### Use
#### Generate a scene
```bash
cd src/scripts
python generate_scene.py --setting_path path/to/levels
```
Then the scene will be saved automatically in `levels/level_name/`.

#### Load a scene to explore yourself
```bash
cd src/scripts
python load_scene.py --scene_path path/to/levels
```

#### Run evaluation
The options for the evalution are listed as following:
```bash
usage: main.py [-h] [--level LEVEL] [--model MODEL] [--room_number ROOM_NUMBER] [--record_path RECORD_PATH] [--history_type HISTORY_TYPE] [--hint]
               [--max_history MAX_HISTORY] [--max_retry MAX_RETRY]

options:
  -h, --help            show this help message and exit
  --level LEVEL         level name
  --model MODEL         model name
  --room_number ROOM_NUMBER
                        room number of the level generated
  --record_path RECORD_PATH
                        record path to load
  --history_type HISTORY_TYPE
                        history type, asserted in full, key, max
  --hint                whether to use hint
  --max_history MAX_HISTORY
                        max history length
  --max_retry MAX_RETRY
                        max retry times
```
For example, you can load the third scene generated for level3 and evaluate the model `gpt-4o` with the history type `full`:
```bash
cd src
python main.py --level level3 --room_number 3 --model gpt-4o --history_type full
```

If you want load a record, you can use the following command:
```bash
cd src
python main.py --level level3 --room_number 3 --model record --history_type full --record_path path/to/record
```
This will start a game re-playing the record.


#### Story Recovery & MultiRoom & Extensions

> coming soon!


## Citation
If you find this repository useful, please cite our paper:
```bibtex
@misc{wang2025multimodallargelanguagemodels,
      title={How Do Multimodal Large Language Models Handle Complex Multimodal Reasoning? Placing Them in An Extensible Escape Game}, 
      author={Ziyue Wang and Yurui Dong and Fuwen Luo and Minyuan Ruan and Zhili Cheng and Chi Chen and Peng Li and Yang Liu},
      year={2025},
      eprint={2503.10042},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2503.10042}, 
}
```
