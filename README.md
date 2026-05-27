# 本地 AI 翻唱工作台

这个项目不是从零训练大模型，而是把现成工具串成一条稳定流程：

1. 录你的声音。
2. 用 Applio/RVC 训练你的音色模型。
3. 把目标歌曲分离成原唱人声和伴奏。
4. 用你的模型把原唱人声转换成你的音色。
5. 把转换后的人声和伴奏重新混音。

这样可以绕开“自己唱歌跑调”的问题：原唱人声负责音准、节奏、咬字和气口，你的录音负责提供音色。

## 先装什么

必装：

- Python 3.10+。你当前机器已经有 Python 3.12，可以运行本项目脚本。
- ffmpeg。Windows 上可以用：

```powershell
winget install Gyan.FFmpeg
```

推荐另装：

- Applio：用于 RVC 训练和推理。
- Audacity 或 Reaper：用于听感检查和精修混音。
- Demucs：可选，用命令行做人声分离；如果你更喜欢 GUI，可以直接用 Applio 的 UVR。

## 初始化

```powershell
python .\voice_cover.py init
python .\voice_cover.py doctor
```

`init` 会创建这些核心目录：

- `recordings/raw/`：放你的原始录音。
- `datasets/`：放清洗和切片后的训练数据。
- `songs/originals/`：放原曲或 30-60 秒测试片段。
- `songs/stems/`：放分离出来的人声和伴奏。
- `songs/converted_vocals/`：放 Applio/RVC 输出的“你的声音版人声”。
- `models/`：放你的 `.pth` 和 `.index` 模型文件。
- `outputs/`：放最终混音。

## 录音建议

快速 demo 可以先录 3-5 分钟，但想稳定像你，建议录 10-30 分钟。

素材要求：

- 尽量干声：无伴奏、无混响、少底噪。
- 手机也可以，但离麦稳定，不要喷麦。
- 包含说话、哼唱、长元音、低中高音区、轻声和正常力度。
- 每段 10-30 秒都可以，后面脚本会切成训练片段。

## 制作训练数据

把你的录音放进 `recordings/raw/`，然后运行：

```powershell
python .\voice_cover.py make-dataset recordings/raw --name my_voice --trim-silence --denoise
```

脚本会输出：

- `datasets/my_voice/raw/`
- `datasets/my_voice/clean/`
- `datasets/my_voice/segments/`
- `datasets/my_voice/manifest.csv`

在 Applio 里训练时，训练数据目录选择：

```text
datasets/my_voice/segments
```

推荐 Applio 初始设置：

- Sample rate：48k
- F0 method：RMVPE
- RTX 4060 Laptop 8GB 首次 batch size：6-8
- Epochs：先试 200-400

训练完成后，把模型文件整理到：

```text
models/my_voice/
```

建议命名：

```text
models/my_voice/my_voice.pth
models/my_voice/my_voice.index
```

## 先做 60 秒测试

不要第一把就跑整首歌。先从一首歌里切 60 秒：

```powershell
python .\voice_cover.py trim-test songs/originals/song.wav --name song --start 00:00:45 --duration 60
```

## 分离原唱人声和伴奏

路线 A：用 Applio/UVR GUI

1. 在 Applio 里打开 UVR。
2. 输入 `songs/originals/song_test.wav` 或完整歌曲。
3. 导出 vocal 和 instrumental。
4. 导入本项目：

```powershell
python .\voice_cover.py import-stems --name song --vocals "D:\path\to\vocals.wav" --instrumental "D:\path\to\instrumental.wav"
```

路线 B：用 Demucs 命令行

先安装 Demucs 后运行：

```powershell
python .\voice_cover.py separate songs/originals/song_test.wav --name song --device cuda
```

输出会在：

```text
songs/stems/song/vocals.wav
songs/stems/song/instrumental.wav
```

## 用 Applio 把原唱换成你的音色

在 Applio/RVC 推理界面：

- 模型选择：`models/my_voice/my_voice.pth`
- Index 选择：`models/my_voice/my_voice.index`
- 输入音频：`songs/stems/song/vocals.wav`
- 输出位置建议：`songs/converted_vocals/song_my_voice.wav`

初始推理参数：

- F0 method：RMVPE
- Index/search ratio：0.5
- Protect consonants：0.33
- Clean audio：如果分离人声有毛刺就打开

如果原唱和你的真实音区差很多，先试着在 Applio 里调 transpose/key，再判断音色。

## 混音

Applio 输出转换后的人声后，运行：

```powershell
python .\voice_cover.py mix --name song --vocals songs/converted_vocals/song_my_voice.wav --reverb subtle --vocal-eq
```

如果人声太小：

```powershell
python .\voice_cover.py mix --name song --vocals songs/converted_vocals/song_my_voice.wav --vocal-gain-db 2
```

如果人声比伴奏慢 80ms：

```powershell
python .\voice_cover.py mix --name song --vocals songs/converted_vocals/song_my_voice.wav --vocal-offset-ms -80
```

最终文件会输出到：

```text
outputs/song_mix.wav
```

## 生成单曲检查单

这个命令会生成一份 Applio 手动操作清单，里面带好绝对路径：

```powershell
python .\voice_cover.py checklist --voice my_voice --song song
```

生成位置：

```text
reports/
```

## 常见问题

不像你的声音：

- 录音太少或太单一。补 10-30 分钟更干净的素材。
- 多补一些唱歌素材，尤其是目标歌曲涉及的音区。

唱歌部分假、金属感强：

- 原唱音区和你差太远，试着降调或升调。
- 分离出来的人声有杂音，换 UVR/Demucs 模型重新分离。
- Applio 里降低或调整 index/search ratio。

咬字糊：

- 数据集降噪太重，重新用更轻的清洗。
- Applio 的 protect consonants 稍微调高。

伴奏和人声对不齐：

- 用 `--vocal-offset-ms` 微调。
- 正数表示延迟人声，负数表示延迟伴奏。

## 边界

默认只用于个人练习和自娱自乐。只训练你自己的声音，不要伪装成别人，也不要直接公开发布未经授权的歌曲翻唱。
