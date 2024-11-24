import requests

import os,time,sys
from pathlib import Path
ROOT_DIR=Path(__file__).parent.as_posix()

# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = ROOT_DIR + f';{ROOT_DIR}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = ROOT_DIR + f':{ROOT_DIR}/ffmpeg:' + os.environ['PATH']
    
os.environ['MODELSCOPE_CACHE'] = ROOT_DIR + "/models"
os.environ['HF_HOME'] = ROOT_DIR + "/models"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
os.environ['HF_HOME']=Path(f"{ROOT_DIR}/models").as_posix()
Path(os.environ['HF_HOME']).mkdir(parents=True, exist_ok=True)
sys.path.append('{}/third_party/Matcha-TTS'.format(root_dir))


from cosyvoice.cli.cosyvoice import CosyVoice
from cosyvoice.utils.file_utils import load_wav
import torchaudio

cosyvoice = CosyVoice('pretrained_models/CosyVoice-300M-SFT', load_jit=True, load_onnx=False, fp16=True)
# sft usage
print(cosyvoice.list_avaliable_spks())
# change stream=True for chunk stream inference


# 1. 根据固定角色配音

for i, j in enumerate(cosyvoice.inference_sft('你好，我是通义生成式语音大模型，请问有什么可以帮您的吗？', '中文女', stream=False)):
    torchaudio.save('sft_{}.wav'.format(i), j['tts_speech'], 22050)


## 2.同语言音色克隆

cosyvoice = CosyVoice('pretrained_models/CosyVoice-300M') # or change to pretrained_models/CosyVoice-300M for 50Hz inference
# zero_shot usage, <|zh|><|en|><|jp|><|yue|><|ko|> for Chinese/English/Japanese/Cantonese/Korean
prompt_speech_16k = load_wav('zero_shot_prompt.wav', 16000)
for i, j in enumerate(cosyvoice.inference_zero_shot('收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。', '希望你以后能够做的比我还好呦。', prompt_speech_16k, stream=False)):
    torchaudio.save('zero_shot_{}.wav'.format(i), j['tts_speech'], 22050)

# cross_lingual usage
## 3. 跨语言克隆
prompt_speech_16k = load_wav('cn.wav', 16000)
for i, j in enumerate(cosyvoice.inference_cross_lingual("""
<|zh|>收到好友从远方寄来的生日礼物，
那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐
笑容如花儿般绽放""", prompt_speech_16k, stream=False)):
    torchaudio.save('cross_lingual_{}.wav'.format(i), j['tts_speech'], 22050)

