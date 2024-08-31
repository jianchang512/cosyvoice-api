# 适用于 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) 的 API 接口项目

> 由于 CosyVoice 官方未提供api接口，为方便使用，而创建本api项目，若要使用，需提前先安装部署好 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)



## 使用方法

> 先部署好 CosyVoice，具体部署方法参考 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)，如果是windows部署，可参考博客文章 https://juejin.cn/post/7389946395066368035

1. 下载本仓库中 api.py 文件，然后复制到 CosyVoice 项目下同 webui.py 放于同一目录中
2. 安装模块 `flask`和`waitress`, 安装命令 `pip install flask waitress`
3. 启动api服务，`python api.py`
4. 如果要合成多行文本，需要提前安装 ffmpeg




# 在 [pyVideoTrans视频翻译软件](https://github.com/jianchang512/pyvideotrans) 中使用
![image](https://github.com/user-attachments/assets/cb53d9a9-9030-4227-ad94-e8b6b435dbcf)


1. 首先升级视频翻译软件到2.08+
2. 确保已部署CosyVoice项目，已将 CosyVoice-api中的api.py放入，并成功启动了 api.py。
3. 打开视频翻译软件，左上角设置--CosyVoice：填写 api 地址，默认是 `http://127.0.0.1:9233`
4. 填写参考音频和音频对应文字 

```
参考音频填写：

每行都由#符号分割为两部分，第一部分是wav音频路径，第二部分是该音频对应的文字内容，可填写多行。

wav音频最佳时长5-15s，如果音频放在了CosyVoice项目的根路径下，即webui.py同目录下，这里直接填写名称即可.
如果放在了根目录下的wavs目录下，那么需要填写 wavs/音频名称.wav

参考音频填写示例：

1.wav#你好啊亲爱的朋友
wavs/2.wav#你好啊朋友们

```
5. 填写完毕后，主界面中配音渠道选择 CosyVoice, 角色选择对应的即可。其中 clone 角色是复制原视频中的音色

> **2.11版起，pyVideoTrans视频翻译软件已支持使用 [v3ucn/CosyVoice_For_Windows整合包](https://github.com/v3ucn/CosyVoice_For_Windows) 的 api 接口，可直接填写该整合包的api地址，默认`http://127.0.0.1:9880`,注意端口`9880`不可更改，以此判断是整合包的api接口, 角色名仍按上方参考音频方式填写，即`角色名#对应文本可随便填`**


----

----

## 在其他整合包中使用该api

**建议该 api.py 配合 conda 源码部署后使用，如果用于第三方整合包，可能存在兼容问题，Win上conda部署CosyVoice方法 https://juejin.cn/post/7389946395066368035**


>如果使用的是 https://github.com/v3ucn/CosyVoice_For_Windows 这个整合包，那么下载本项目的`api.py`文件，替换原整合包里的`api.py`文件，然后用记事本打开 `启动接口服务.bat` ，将倒数第三行开头的`@REM`删掉,保存后双击该bat文件启动。如下图
>![image](https://github.com/user-attachments/assets/a4ee924e-f210-48e4-a0c2-09e881a36cf6)


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
