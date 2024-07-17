# 适用于 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) 的 API 接口项目

> 由于 CosyVoice 官方未提供api接口，为方便使用，而创建本api项目，若要使用，需提前先安装部署好 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)



## 使用方法

> 先部署好 CosyVoice，具体部署方法参考 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)，如果是windows部署，可参考博客文章 https://juejin.cn/post/7389946395066368035

1. 下载本仓库中 api.py 文件，然后复制到 CosyVoice 项目下同 webui.py 放于同一目录中
2. 安装模块 `flask`和`waitress`, 安装命令 `pip install flask waitress`
3. 启动api服务，`python api.py`
4. 如果要合成多行文本，需要提前安装 ffmpeg


## 在其他整合包中时

1. 首先确保整合包可以正常运行webui
2. 复制此api.py到整合包内
3. 查看整合包内的python路径，执行 `python api.py`, 如果整合包内存在 bat 文件，可以记事本打开，查看 python.exe 所在路径，例如路径为 '.\py311\python.exe',那么执行命令`.\py311\python.exe api.py` 


## 接口信息

默认接口地址是 `http://127.0.0.1:9233`


对外有3个接口，分别如下

**单纯语音合成接口**

> api地址: {api url}/tts
>
> 参数：
> 
> text:待合成的文本
> 
> role:预置语音角色 "中文男|中文女|英文男|英文女|日语男|韩语女|粤语女" 选其一

请求示例

```
import requests

data={
    "text":"你好啊亲爱的朋友们，今天天气不错，暴风骤雨哗哗的。",
    "role":"中文女"
}

response=requests.post(f'http://127.0.0.1:9233/tts',data=data,timeout=3600)


if response.status_code!=200:
    # 出错了
    print(response.json())
else:
    # 返回的wav数据流，可直接保存
    with open("./tts.wav",'wb') as f:
        f.write(response.content)

```


**同语言克隆**

> api地址: {url}/clone_eq
>
> 参数：
>
> text:待合成的文字
> 
> reference_audio:需要克隆音色的参考音频wav，5-10s最佳
> 
> reference_text:该参考音频对应的文本内容

请求示例

```
import requests

data={
    "text":"你好啊亲爱的朋友们，今天天气不错，暴风骤雨哗哗的。",
    "reference_audio":"10.wav",
    "reference_text":"参考音频10.wav对应的文本内容"
}

response=requests.post(f'http://127.0.0.1:9233/tts',data=data,timeout=3600)


if response.status_code!=200:
    # 出错了
    print(response.json())
else:
    # 返回的wav数据流，可直接保存
    with open("./clone_eq.wav",'wb') as f:
        f.write(response.content)

```


**跨语言克隆**

> 地址： /clone_mul
> 
> 参数:
>
> text:待克隆的文字
> 
> lang:text文字对应的语言代码  “zh|en|jp|ko|yue”
> 
> reference_audio:要克隆音色的参考音频wav

请求示例：

```
import requests

data={
    "text":"hello,my friend,I hope you a happy day.",
    "lang":"en"
    "reference_audio":"10.wav",
}

response=requests.post(f'http://127.0.0.1:9233/tts',data=data,timeout=3600)


if response.status_code!=200:
    # 出错了
    print(response.json())
else:
    # 返回的wav数据流，可直接保存
    with open("./clone_eq.wav",'wb') as f:
        f.write(response.content)

```


## API 使用注意问题

1. 当一行文字中有句话`。`时，有时会发生只合成了句话之前的文字，句号之后的没有合成，为避免该问题，已自动将句话替换为了逗号`，`。
2. api.py 支持合成多行文字，例如1000行，前提是需要预先安装 ffmpeg，在实际合成中，将按行依次合成，然后再使用ffmpeg将所有合成片段连接为一个文件。
3. 一行不要太长，否则合成很慢，效果也不佳。
4. 使用api.py 需额外安装 `flask`和`waitress`这2个模块
5. 预先只加载了用于单纯文字合成语音的模型，没有预加载克隆模型，第一次使用时才会加载模型，因此第一次使用克隆音色时可能比较慢。
