##  整合包不含 CosyVoice-300M-Instruct 和 CosyVoice-ttsfrd 模型，若需要，请执行   .\runtime\python download.py 下载

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




# SDK模型下载
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice-300M', local_dir='pretrained_models/CosyVoice-300M')
snapshot_download('iic/CosyVoice-300M-25Hz', local_dir='pretrained_models/CosyVoice-300M-25Hz')
snapshot_download('iic/CosyVoice-300M-SFT', local_dir='pretrained_models/CosyVoice-300M-SFT')
snapshot_download('iic/CosyVoice-300M-Instruct', local_dir='pretrained_models/CosyVoice-300M-Instruct')
snapshot_download('iic/CosyVoice-ttsfrd', local_dir='pretrained_models/CosyVoice-ttsfrd')


