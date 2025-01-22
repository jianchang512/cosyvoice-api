import os,time,sys
from pathlib import Path
root_dir=Path(__file__).parent.as_posix()

# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = root_dir + f';{root_dir}\\ffmpeg;' + os.environ['PATH']+f';{root_dir}/third_party/Matcha-TTS'
else:
    os.environ['PATH'] = root_dir + f':{root_dir}/ffmpeg:' + os.environ['PATH']
    os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':third_party/Matcha-TTS'
sys.path.append(f'{root_dir}/third_party/Matcha-TTS')
tmp_dir=Path(f'{root_dir}/tmp').as_posix()
logs_dir=Path(f'{root_dir}/logs').as_posix()
os.makedirs(tmp_dir,exist_ok=True)
os.makedirs(logs_dir,exist_ok=True)

from flask import Flask, request, render_template, jsonify,  send_from_directory,send_file,Response, stream_with_context,make_response,send_file
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import shutil
import datetime
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
from cosyvoice.utils.file_utils import load_wav


import torchaudio,torch
from pathlib import Path
import base64


# 下载模型
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')
snapshot_download('iic/CosyVoice-300M-SFT', local_dir='pretrained_models/CosyVoice-300M-SFT')



'''
app logs
'''
# 配置日志
# 禁用 Werkzeug 默认的日志处理器
log = logging.getLogger('werkzeug')
log.handlers[:] = []
log.setLevel(logging.WARNING)

root_log = logging.getLogger()  # Flask的根日志记录器
root_log.handlers = []
root_log.setLevel(logging.WARNING)

app = Flask(__name__, 
    static_folder=root_dir+'/tmp', 
    static_url_path='/tmp')

app.logger.setLevel(logging.WARNING) 
# 创建 RotatingFileHandler 对象，设置写入的文件路径和大小限制
file_handler = RotatingFileHandler(logs_dir+f'/{datetime.datetime.now().strftime("%Y%m%d")}.log', maxBytes=1024 * 1024, backupCount=5)
# 创建日志的格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 设置文件处理器的级别和格式
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
# 将文件处理器添加到日志记录器中
app.logger.addHandler(file_handler)



sft_model = None
tts_model = None 

VOICE_LIST=['中文女', '中文男', '日语男', '粤语女', '英文女', '英文男', '韩语女']





def base64_to_wav(encoded_str, output_path):
    if not encoded_str:
        raise ValueError("Base64 encoded string is empty.")

    # 将base64编码的字符串解码为字节
    wav_bytes = base64.b64decode(encoded_str)

    # 检查输出路径是否存在，如果不存在则创建
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 将解码后的字节写入文件
    with open(output_path, "wb") as wav_file:
        wav_file.write(wav_bytes)

    print(f"WAV file has been saved to {output_path}")


# 获取请求参数
def get_params(req):
    params={
        "text":"",
        "lang":"",
        "role":"中文女",
        "reference_audio":None,
        "reference_text":"",
        "speed":1.0
    }
    # 原始字符串
    params['text'] = req.args.get("text","").strip() or req.form.get("text","").strip()
    
    # 字符串语言代码
    params['lang'] = req.args.get("lang","").strip().lower() or req.form.get("lang","").strip().lower()
    # 兼容 ja语言代码
    if params['lang']=='ja':
        params['lang']='jp'
    elif params['lang'][:2] == 'zh':
        # 兼容 zh-cn zh-tw zh-hk
        params['lang']='zh'
    
    # 角色名 
    role = req.args.get("role","").strip() or req.form.get("role",'')
    if role:
        params['role']=role
    
    # 要克隆的音色文件    
    params['reference_audio'] = req.args.get("reference_audio",None) or req.form.get("reference_audio",None)
    encode=req.args.get('encode','') or req.form.get('encode','')
    if  encode=='base64':
        tmp_name=f'tmp/{time.time()}-clone-{len(params["reference_audio"])}.wav'
        base64_to_wav(params['reference_audio'],root_dir+'/'+tmp_name)
        params['reference_audio']=tmp_name
    # 音色文件对应文本
    params['reference_text'] = req.args.get("reference_text",'').strip() or req.form.get("reference_text",'')
    
    return params


def del_tmp_files(tmp_files: list):
    print('正在删除缓存文件...')
    for f in tmp_files:
        if os.path.exists(f):
            print('删除缓存文件:', f)
            os.remove(f)


# 实际批量合成完毕后连接为一个文件
def batch(tts_type,outname,params):
    global sft_model,tts_model
    if not shutil.which("ffmpeg"):
        raise Exception('必须安装 ffmpeg')    
    prompt_speech_16k=None
    if tts_type!='tts':
        if not params['reference_audio'] or not os.path.exists(f"{root_dir}/{params['reference_audio']}"):
            raise Exception(f'参考音频未传入或不存在 {params["reference_audio"]}')
        ref_audio=f"{tmp_dir}/-refaudio-{time.time()}.wav" 
        try:
            subprocess.run(["ffmpeg","-hide_banner", "-ignore_unknown","-y","-i",params['reference_audio'],"-ar","16000",ref_audio],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE,
                   encoding="utf-8",
                   check=True,
                   text=True,
                   creationflags=0 if sys.platform != 'win32' else subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            raise Exception(f'处理参考音频失败:{e}')
        
        prompt_speech_16k = load_wav(ref_audio, 16000)

    text=params['text']
    audio_list=[]
    if tts_type=='tts':
        if sft_model is None:
            sft_model = CosyVoice('pretrained_models/CosyVoice-300M-SFT', load_jit=True, load_onnx=False)

        # 仅文字合成语音
        for i, j in enumerate(sft_model.inference_sft(text, params['role'],stream=False,speed=params['speed'])):
            audio_list.append(j['tts_speech'])
            
    elif tts_type=='clone_eq' and params.get('reference_text'):
        if tts_model is None:
            tts_model=CosyVoice2('pretrained_models/CosyVoice2-0.5B', load_jit=True, load_onnx=False, load_trt=False)

        for i, j in enumerate(tts_model.inference_zero_shot(text,params.get('reference_text'),prompt_speech_16k, stream=False,speed=params['speed'])):
            audio_list.append(j['tts_speech'])

    else:
        if tts_model is None:
            tts_model=CosyVoice2('pretrained_models/CosyVoice2-0.5B', load_jit=True, load_onnx=False, load_trt=False)

        for i, j in enumerate(tts_model.inference_cross_lingual(text,prompt_speech_16k, stream=False,speed=params['speed'])):
            audio_list.append(j['tts_speech'])
    audio_data = torch.concat(audio_list, dim=1)
    
    torchaudio.save(tmp_dir + '/' + outname,audio_data, 22050, format="wav")   
    
    print(f"音频文件生成成功：{tmp_dir}/{outname}")
    return tmp_dir + '/' + outname


# 单纯文字合成语音
@app.route('/tts', methods=['GET', 'POST'])        
def tts():
    params=get_params(request)
    if not params['text']:
        return make_response(jsonify({"code":1,"msg":'缺少待合成的文本'}), 500)  # 设置状态码为500
        
    try:
        # 仅文字合成语音
        outname=f"tts-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}.wav"
        outname=batch(tts_type='tts',outname=outname,params=params)
    except Exception as e:
        print(e)
        return make_response(jsonify({"code":2,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')
    


# 跨语言文字合成语音      
@app.route('/clone_mul', methods=['GET', 'POST'])        
@app.route('/clone', methods=['GET', 'POST'])        
def clone():

    try:
        params=get_params(request)
        if not params['text']:
            return make_response(jsonify({"code":6,"msg":'缺少待合成的文本'}), 500)  # 设置状态码为500
            
        outname=f"clone-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}.wav"
        outname=batch(tts_type='clone',outname=outname,params=params)
    except Exception as e:
        return make_response(jsonify({"code":8,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')
@app.route('/clone_eq', methods=['GET', 'POST'])         
def clone_eq():

    try:
        params=get_params(request)
        if not params['text']:
            return make_response(jsonify({"code":6,"msg":'缺少待合成的文本'}), 500)  # 设置状态码为500
        if not params['reference_text']:
            return make_response(jsonify({"code":6,"msg":'同语言克隆必须传递引用文本'}), 500)  # 设置状态码为500
            
        outname=f"clone-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}.wav"
        outname=batch(tts_type='clone_eq',outname=outname,params=params)
    except Exception as e:
        return make_response(jsonify({"code":8,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')
     

@app.route('/v1/audio/speech', methods=['POST'])
def audio_speech():
    """
    兼容 OpenAI /v1/audio/speech API 的接口
    """
    import random

    if not request.is_json:
        return jsonify({"error": "请求必须是 JSON 格式"}), 400

    data = request.get_json()

    # 检查请求中是否包含必要的参数
    if 'input' not in data or 'voice' not in data:
        return jsonify({"error": "请求缺少必要的参数： input, voice"}), 400
    

    text = data.get('input')
    speed =  float(data.get('speed',1.0))
    
    voice = data.get('voice','中文女')
    params = {}
    params['text']=text
    params['speed']=speed
    api_name='tts'
    if voice in VOICE_LIST:
        params['role']=voice
    elif Path(voice).exists() or Path(f'{root_dir}/{voice}').exists():
        api_name='clone'
        params['reference_audio']=voice
    else:
        return jsonify({"error": {"message": f"必须填写配音角色名或参考音频路径", "type": e.__class__.__name__, "param": f'speed={speed},voice={voice},input={text}', "code": 400}}), 500

    
    filename=f'openai-{len(text)}-{speed}-{time.time()}-{random.randint(1000,99999)}.wav'
    try:
        outname=batch(tts_type=api_name,outname=filename,params=params)
        return send_file(outname, mimetype='audio/x-wav')
    except Exception as e:
        return jsonify({"error": {"message": f"{e}", "type": e.__class__.__name__, "param": f'speed={speed},voice={voice},input={text}', "code": 400}}), 500
         
if __name__=='__main__':
    host='127.0.0.1'
    port=9233
    print(f'\n启动api:http://{host}:{port}\n')
    try:
        from waitress import serve
    except Exception:
        app.run(host=host, port=port)
    else:
        serve(app,host=host, port=port)
    

'''


## 根据内置角色合成文字

- 接口地址:  /tts 
  
- 单纯将文字合成语音，不进行音色克隆

- 必须设置的参数：
 
 `text`:需要合成语音的文字
 
 `role`: '中文女', '中文男', '日语男', '粤语女', '英文女', '英文男', '韩语女' 选择一个

- 成功返回:wav音频数据

- 示例代码
```
data={
    "text":"你好啊亲爱的朋友们",
    "reference_audio":"10.wav"
}

response=requests.post(f'http://127.0.0.1:9933/tts',data=data,timeout=3600)
```


## 同语言克隆音色合成  

- 地址：/clone_eq

参考音频发音语言和需要合成的文字语言一致，例如参考音频是中文发音，同时需要根据该音频将中文文本合成为语音

- 必须设置参数:

`text`： 需要合成语音的文字

`reference_audio`：需要克隆音色的参考音频

`reference_text`：参考音频对应的文字内容 *参考音频相对于 api.py 的路径，例如引用1.wav，该文件和api.py在同一文件夹内，则填写 `1.wav`*

- 成功返回:wav数据

- 示例代码
```
data={
    "text":"你好啊亲爱的朋友们。",
    "reference_audio":"10.wav",
    "reference_text":"希望你过的比我更好哟。"
}

response=requests.post(f'http://127.0.0.1:9933/tts',data=data,timeout=3600)
```

## 不同语言音色克隆: 

- 地址： /cone

参考音频发音语言和需要合成的文字语言不一致，例如需要根据中文发音的参考音频，将一段英文文本合成为语音。

- 必须设置参数:

`text`： 需要合成语音的文字

`reference_audio`：需要克隆音色的参考音频 *参考音频相对于 api.py 的路径，例如引用1.wav，该文件和api.py在同一文件夹内，则填写 `1.wav`*

- 成功返回:wav数据


- 示例代码
```
data={
    "text":"親友からの誕生日プレゼントを遠くから受け取り、思いがけないサプライズと深い祝福に、私の心は甘い喜びで満たされた！。",
    "reference_audio":"10.wav"
}

response=requests.post(f'http://127.0.0.1:9933/tts',data=data,timeout=3600)
```



## 兼容openai tts

- 接口地址 /v1/audio/speech
- 请求方法  POST
- 请求类型  Content-Type: application/json
- 请求参数
    `input`: 要合成的文字
    `model`: 固定 tts-1, 兼容openai参数，实际未使用
    `speed`: 语速，默认1.0
    `reponse_format`：返回格式，固定wav音频数据
    `voice`: 仅用于文字合成时，取其一 '中文女', '中文男', '日语男', '粤语女', '英文女', '英文男', '韩语女'


> 用于克隆时，填写引用的参考音频相对于 api.py 的路径，例如引用1.wav，该文件和api.py在同一文件夹内，则填写 `1.wav`

- 示例代码

```
from openai import OpenAI

client = OpenAI(api_key='12314', base_url='http://127.0.0.1:9933/v1')
with  client.audio.speech.with_streaming_response.create(
                    model='tts-1',
                    voice='中文女',
                    input='你好啊，亲爱的朋友们',
                    speed=1.0                    
                ) as response:
    with open('./test.wav', 'wb') as f:
       for chunk in response.iter_bytes():
            f.write(chunk)


```

'''
