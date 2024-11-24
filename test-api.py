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

# test 单纯文字合成
def api1():
    data={
        "text":"国内各类中文TTS方案层出不穷，也都挺优秀。",
        "role":"中文女"
    }

    response=requests.post(f'http://127.0.0.1:9233/tts',data=data,timeout=3600)

    if response.status_code!=200:
        # 出错了
        print(response.json())
    else:
        # 返回的wav数据流，可直接保存
        with open("./api1.wav",'wb') as f:
            f.write(response.content)

# 同语言克隆
def api2():
    data={
        "text":"国内各类中文TTS方案层出不穷，也都挺优秀。",
        "reference_audio":"cn.wav",
        "reference_text":"希望你以后能够做的比我还好呦"
    }

    response=requests.post(f'http://127.0.0.1:9233/clone_eq',data=data,timeout=3600)

    if response.status_code!=200:
        # 出错了
        print(response.json())
    else:
        # 返回的wav数据流，可直接保存
        with open("./api2.wav",'wb') as f:
            f.write(response.content)


# 不同语言克隆
def api3():
    data={
        "text":"hello,my dear friend, today is good",
        "lang":"en",
        "reference_audio":"cn.wav"
    }

    response=requests.post(f'http://127.0.0.1:9233/clone_mul',data=data,timeout=3600)

    if response.status_code!=200:
        # 出错了
        print(response.json())
    else:
        # 返回的wav数据流，可直接保存
        with open("./api3.wav",'wb') as f:
            f.write(response.content)


api1()
api2()
api3()