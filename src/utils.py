import json
import random

from PIL import Image, ImageDraw, ImageFont
from legent import get_mesh_size

from config import *


def format_scene(scene_path):
    with open(scene_path, "r", encoding="utf-8") as f:
        _ori_scene = f.read()
        
    _scene = _ori_scene.replace(r"{__PREFAB_DIR__}", PREFAB_DIR)
    _scene = _scene.replace("\\", "/").replace("//", "/")
    
    return json.loads(_scene)

def get_scale(prefab, target_size_y):
    __origin_size = get_mesh_size(prefab)
    
    __scale_size = target_size_y / __origin_size[1]

    __scale = [__scale_size for _ in range(len(__origin_size))]

    return __scale

def generate_texture(
    size = (200, 160),
    font_size=36,
    font_path=None,
    rotation_range=(-30, 30),
    noise_points=40,
    noise_lines=4,
    save_path='captcha.png'
):
    captcha_text = ''.join(random.choices('0123456789', k=4))
    width, height = size
    
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except IOError:
        font = ImageFont.load_default()
        font_size = font_size
    
    text_bbox = draw.textbbox((0, 0), captcha_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (width - text_width) / 2
    y = (height - text_height) / 2 - 5
    
    for i, char in enumerate(captcha_text):
        char_img = Image.new('RGBA', (font_size, font_size), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((0, 0), char, font=font, fill=(0, 0, 0, 255))
        
        # rotate the character randomly
        rotation_angle = random.randint(rotation_range[0], rotation_range[1])
        char_img = char_img.rotate(rotation_angle, expand=True)
        
        char_bbox = char_img.getbbox()
        char_width = char_bbox[2] - char_bbox[0]
        char_height = char_bbox[3] - char_bbox[1]
        
        char_x = x + i * (font_size * 0.8) - (char_width - font_size) / 2 - width / 8
        char_y = y - (char_height - font_size) / 2
        
        img.paste(char_img, (int(char_x), int(char_y)), char_img)
    
    # add noise lines
    for _ in range(noise_lines):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
    
    # add noise points
    for _ in range(noise_points):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(150, 200),) * 3)
    
    
    img = swap_image_quarters(img)
    
    img.save(save_path)
    return captcha_text

def swap_image_quarters(img):
    """ cut image into four quarters and swap them """
    width, height = img.size
    w_half, h_half = width // 2, height // 2

    top_left = img.crop((0, 0, w_half, h_half)) 
    top_right = img.crop((w_half, 0, width, h_half)) 
    bottom_left = img.crop((0, h_half, w_half, height))
    bottom_right = img.crop((w_half, h_half, width, height))

    new_img = Image.new('RGB', (width, height))

    new_img.paste(bottom_right, (0, 0))
    new_img.paste(bottom_left, (w_half, 0))
    new_img.paste(top_right, (0, h_half))
    new_img.paste(top_left, (w_half, h_half))

    return new_img



