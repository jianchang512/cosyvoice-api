
这是用于 [CosyVoice2](https://github.com/FunAudioLLM/CosyVoice) 的 api 文件，部署好 cosyVoice 项目后，将该 `api.py` 文件同 `webui.py`放在一起，然后执行 `python api.py`。

如果是三方整合包，将 `api.py` 同 bat 脚本放在一起，然后查找其中`python.exe`所在的位置，在bat所在当前文件夹地址栏中输入`cmd`回车，然后执行 `目录/python.exe api.py`

如果执行时提示`module flask not found`,请执行 ` python.exe -m pip install flask` 安装


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
