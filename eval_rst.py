import os, sys
import json, argparse
from collections import defaultdict
from tqdm import tqdm 

def scene_iter(path, level="level1", scene_count=10, round_id=1, model=None):
    level_dirs = [os.path.join(path, f"{level}-{i}") for i in range(1, scene_count+1)]

    rst = defaultdict(dict)
    models = []
    for level_scene in tqdm(level_dirs, leave=len(level_dirs)):
        scene_id = level_scene.split(f'{level}-')[-1]
        if not os.path.exists(level_scene):
            continue

        for model_dir in os.listdir(level_scene):
            if model is not None:
                if not model in model_dir: continue
            if model_dir.startswith('.'): continue
            
            toks = model_dir.split(f"_t_{round_id}")
            if len(toks) < 2: continue
            model_name = toks[0]

            if not model_name in models:
                models.append(model_name)
                rst[model_name] = defaultdict(dict)

            record_file = os.path.join(level_scene, model_dir, 'records.json')
            if not os.path.exists(record_file):
                #import pdb; pdb.set_trace()
                rst[model_name][scene_id]['success'] = 0
                rst[model_name][scene_id]['grab'] = 0
                rst[model_name][scene_id]['grab_attempts'] = 0
                rst[model_name][scene_id]['grab_success'] = 0
                rst[model_name][scene_id]['step'] = 50 if level == "level1" else 100
            else:
                with open(record_file) as fr:
                    record = json.loads(fr.read())

                escaped = False

                # for success
                if record[-1].get('info', None) is not None:
                    rst[model_name][scene_id]['step'] = record[-2]['step'] + 1
                    if 'Escaped succesfully!' in record[-1]['info']:
                        rst[model_name][scene_id]['success'] = 1
                        escaped = True
                    else:
                        rst[model_name][scene_id]['success'] = 0
                    record_len = len(record) - 1
                    last_inter = record[-2]
                else:
                    if level == "level1":
                        max_step = 50 
                    else:
                        max_step = 75 if level == "level2" else 100
                    rst[model_name][scene_id]['step'] = min(max_step, record[-1]['step'] + 1)
                    rst[model_name][scene_id]['success'] = 0
                    record_len = len(record)
                    last_inter = record[-1]
        
                grab_attempts = sum([_r['response'].get('grab', False) for _r in record if not "info" in _r])
                # For successful trials:
                if level == "level1":
                    grab_tp = 1.
                elif level == "level2":
                    grab_tp = 2.
                elif level.startswith("level3"):
                    grab_tp = 3.

                if grab_attempts:
                    if not escaped:
                        # For unsuccessful trials
                        grab_tp = 0
                        if "key_1" in last_inter["bag"]:
                            print(f"{level_scene.split('/')[-1]} {model_dir} found key_1!")
                            grab_tp += 1
                        if "key_2" in last_inter["bag"]:
                            print(f"{level_scene.split('/')[-1]} {model_dir} found key_2!")
                            grab_tp += 1
                        if "note_1" in last_inter["bag"]:
                            print(f"{level_scene.split('/')[-1]} {model_dir} found note_1!")
                            grab_tp += 1
                        if "note_2" in last_inter["bag"]:
                            print(f"{level_scene.split('/')[-1]} {model_dir} found note_2!")
                            grab_tp += 1

                    #print(model_dir, grab_tp)
                    grab_success = grab_tp / grab_attempts

                else:
                    grab_success = 0

                rst[model_name][scene_id]['grab'] = grab_attempts
                grab_attempts = grab_attempts / float(record_len)
                rst[model_name][scene_id]['grab_attempts'] = grab_attempts
                rst[model_name][scene_id]['grab_success'] = grab_success 

    for model in rst:
        print("\n\n=================")
        print('model: ', model)
        success, step, grab, grab_acc = 0,0,0,0
        for scene_id in rst[model]:
            _success = rst[model][scene_id]["success"] 
            _step = rst[model][scene_id]["step"]
            _grab = rst[model][scene_id]["grab_attempts"]
            _grab_count = rst[model][scene_id]["grab"]
            _grab_acc = rst[model][scene_id]["grab_success"]
            print(f'    {scene_id}: {_success}\t{_step}\t{_grab_count}\t{_grab:.2f}\t{_grab_acc:.2f}')
            success += _success
            step += _step
            grab += _grab
            grab_acc += _grab_acc
        l = float(len(rst[model]))
        print(f'    Escapr Rate: {100*success/l:.2f}%, avg step: {step/l:.2f}, Grab SR: {100*grab_acc/l:.2f}%, Grab Ratio: {grab/l:.3f}')
            

if __name__ == '__main__':
    """
    names of results dirs:  [path_to_game_cache]/[level]/[model_name]-[round_id]
    to run: python eval_rst.py --level level2 --game_cache RoomEscape/game/game_cache
    """
    parser = argparse.ArgumentParser(description='args for calculate resultsn')
    parser.add_argument('--game_cache', type=str, required=True, help="path to your game_cache dir, the sub_dir of game_cache should be ''")
    parser.add_argument('--level', type=str, default=None, help='choose from: level1, level2, level3, etc for single room settings')
    parser.add_argument('--round_id', type=int, default=1, help='if you run the game for multiple trials, round_id is the number of trial')
    args = parser.parse_args()

    level = args.level
    round_id = args.round_id
    game_cache = args.game_cache

    scene_iter(game_cache, level=level, scene_count=11, round_id=round_id)

