import os,time,sys
import os,time,sys
from pathlib import Path
root_dir=Path(__file__).parent.as_posix()

# ffmpeg
if sys.platform == 'win32':
    os.environ['PATH'] = root_dir + f';{root_dir}\\ffmpeg;' + os.environ['PATH']
else:
    os.environ['PATH'] = root_dir + f':{root_dir}/ffmpeg:' + os.environ['PATH']
    
os.environ['MODELSCOPE_CACHE'] = root_dir + "/models"
os.environ['HF_HOME'] = root_dir + "/models"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
os.environ['HF_HOME']=Path(f"{root_dir}/models").as_posix()
Path(os.environ['HF_HOME']).mkdir(parents=True, exist_ok=True)

tmp_dir=Path(f'{root_dir}/tmp').as_posix()
logs_dir=Path(f'{root_dir}/logs').as_posix()
print(f'{root_dir=}')
print(f'{tmp_dir=}')
print(f'{logs_dir=}')
os.makedirs(tmp_dir,exist_ok=True)
os.makedirs(logs_dir,exist_ok=True)
os.makedirs(f'{root_dir}/pretrained_models',exist_ok=True)
sys.path.append('{}/third_party/Matcha-TTS'.format(root_dir))


if sys.platform=='win32':
    os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ';third_party\\Matcha-TTS'
else:
    os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':third_party/Matcha-TTS'



from flask import Flask, request, render_template, jsonify,  send_from_directory,send_file,Response, stream_with_context,make_response
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import shutil
import datetime
from modelscope import snapshot_download
from cosyvoice.cli.cosyvoice import CosyVoice
from cosyvoice.utils.file_utils import load_wav
import torchaudio
from pathlib import Path
import base64





if not os.path.exists('pretrained_models/CosyVoice-300M/cosyvoice.yaml') or not os.path.exists('pretrained_models/CosyVoice-300M-SFT/cosyvoice.yaml'):
    snapshot_download('iic/CosyVoice-300M', cache_dir='pretrained_models/CosyVoice-300M',local_dir='pretrained_models/CosyVoice-300M')
    snapshot_download('iic/CosyVoice-300M-SFT', cache_dir='pretrained_models/CosyVoice-300M-SFT',local_dir='pretrained_models/CosyVoice-300M-SFT')

# 预加载SFT模型
tts_model = CosyVoice('pretrained_models/CosyVoice-300M-SFT')
#tts_model = None
# 懒加载clone模型，在第一次克隆时加载
clone_model = None
#clone_model = CosyVoice('pretrained_models/CosyVoice-300M')


'''
app logs
'''
# 配置日志
# 禁用 Werkzeug 默认的日志处理器
log = logging.getLogger('werkzeug')
log.handlers[:] = []
log.setLevel(logging.WARNING)

app = Flask(__name__, 
    static_folder=root_dir+'/tmp', 
    static_url_path='/tmp')

root_log = logging.getLogger()  # Flask的根日志记录器
root_log.handlers = []
root_log.setLevel(logging.WARNING)
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
        "reference_text":""
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
    if tts_type=='tts':
        # 仅文字合成语音
        output = tts_model.inference_sft(text, params['role'],stream=False)
    elif tts_type=='clone_eq':
        # 同语言克隆
        output=clone_model.inference_zero_shot(text,params['reference_text'],prompt_speech_16k)
    else:
        output = clone_model.inference_cross_lingual(f'<|{params["lang"]}|>{text}', prompt_speech_16k)
    
    torchaudio.save(tmp_dir + '/' + outname, list(output)[0]['tts_speech'], 22050)
    
    
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
        outname=f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}-tts.wav"
        outname=batch(tts_type='tts',outname=outname,params=params)
    except Exception as e:
        print(e)
        return make_response(jsonify({"code":2,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')
    

# 同一种语言音色克隆
@app.route('/clone_eq', methods=['GET', 'POST'])        
def clone_eq():
    global clone_model
    if not clone_model:
        print('第一次克隆加载模型...')
        clone_model = CosyVoice('pretrained_models/CosyVoice-300M')
    try:
        params=get_params(request)
        if not params['text']:
            return make_response(jsonify({"code":3,"msg":'缺少待合成的文本'}), 500)  # 设置状态码为500
        if not params['reference_text']:
            return make_response(jsonify({"code":4,"msg":'必须设置参考音频对应的参考文本reference_text'}), 500)  # 设置状态码为500
            
        outname=f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}-clone_eq.wav"
        outname=batch(tts_type='clone_eq',outname=outname,params=params)
    except Exception as e:
        return make_response(jsonify({"code":5,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')

# 跨语言文字合成语音        
@app.route('/clone_mul', methods=['GET', 'POST'])        
def clone_mul():
    global clone_model
    if not clone_model:
        print('第一次克隆加载模型...')
        clone_model = CosyVoice('pretrained_models/CosyVoice-300M')
    try:
        params=get_params(request)
        if not params['text']:
            return make_response(jsonify({"code":6,"msg":'缺少待合成的文本'}), 500)  # 设置状态码为500
        if not params['lang']:
            return make_response(jsonify({"code":7,"msg":'必须设置待合成文本的语言代码'}), 500)  # 设置状态码为500
            
        outname=f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-')}-clone_mul.wav"
        outname=batch(tts_type='clone_mul',outname=outname,params=params)
    except Exception as e:
        return make_response(jsonify({"code":8,"msg":str(e)}), 500)  # 设置状态码为500
    else:
        return send_file(outname, mimetype='audio/x-wav')
        
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

使用示例，有1个10s时长的wav音频 10.wav，想克隆它的音色，这个音频发音是中文。
想合成的文字是  “你好啊亲爱的朋友们，今天天气不错，暴风骤雨哗哗的。”

import requests

# 单纯将文字合成语音，不进行音色克隆

必须设置的参数：text,role 

# 需要克隆音色进行语音合成

必须设置参数:text,lang,reference_audio


# 单纯文字合成
data={
    "text":"你好啊亲爱的朋友们，今天天气不错，暴风骤雨哗哗的。",
    "role":"中文女"
}
url='/tts'

# 克隆音色合成,当文本语言和音频语言一致时
data={
    "text":"你好啊亲爱的朋友们，今天天气不错，暴风骤雨哗哗的。",
    "reference_audio":"10.wav",
    "reference_text":"10.wav对应的文字内容",
}
url='/clone_eq'


# 克隆音色合成,当文本语言和音频语言不一致时
data={
    "text":"hello, my friend",
    "lang":"en",
    "reference_audio":"10.wav"
}
url='clone_mul'


response=requests.post(f'http://127.0.0.1:9933/{url}',data=data,timeout=3600)


if response.status_code!=200:
    # 出错了
    print(response.json())
else:
    # 返回的wav数据流，可直接保存
    with open("./tts.wav",'wb') as f:
        f.write(response.content)


'''
