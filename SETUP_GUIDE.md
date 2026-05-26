# 🚀 声音克隆系统小白部署指南 (从零开始)

如果您刚刚 Clone 了这个项目，想要在自己的电脑上跑通“声音克隆”的整套流程，请按照本手册一步步操作。

---

## 🛑 第一阶段：准备您的运行环境 (必须要做的配置)

为了让 AI 能在您的电脑上顺利跑起来，您需要安装以下软件：

### 1. 安装 Python
项目需要 Python 3.10 或以上版本。
* 前往 [Python 官网](https://www.python.org/downloads/) 下载并安装。
* **重要提示**：安装时，请务必勾选底部**“Add python.exe to PATH”**（将 Python 添加到环境变量），否则后续无法运行！

### 2. 安装 FFmpeg (音视频处理核心)
AI 处理音频必须用到它。
* 如果您使用 Windows 10/11，只需按下 `Win + X` 打开 **PowerShell(管理员)**。
* 输入并回车执行：`winget install Gyan.FFmpeg`
* 安装完成后，关闭 PowerShell 并重新打开。

### 3. 安装依赖包
打开当前项目所在的文件夹，在地址栏输入 `cmd` 并回车，打开终端。
执行以下命令安装项目所需的 Python 依赖（如果报错，请确保开启了全局代理）：
```cmd
pip install -r requirements.txt
```
*(注：如果您还没生成 requirements.txt，项目中包含了依赖需求，正常运行一次报错缺什么用 pip 补什么即可)*

---

## 📦 第二阶段：安装核心引擎 (Applio) 与底模大文件

本项目的音频处理和模型训练底层依赖于强大的 **Applio**（一款开源的 RVC 变声器界面版）。

### 1. 下载 Applio
* 请前往 [Applio GitHub Releases](https://github.com/IAHispano/Applio/releases) 页面。
* 下载适用于 Windows 的完整压缩包（通常叫做 `Applio-Windows.zip` 或类似名称，约 2~3GB）。
* 解压到您的 C 盘根目录，确保路径为 `C:\Applio`（这样本项目里的 `start_applio.cmd` 脚本才能直接关联上它）。

### 2. 一键下载“AI 底模” (解决克隆后无法运行的问题)
因为 GitHub 无法存放几十个 GB 的“底模”（预训练模型），所以默认 Clone 下来是没法训练的。
为了帮您省去四处找模型下载的麻烦，我们为您准备了一个一键下载脚本 `download_models.py`。

在项目根目录运行它：
```cmd
python download_models.py
```
*(脚本会自动从 HuggingFace 帮您把 HuBERT、RMVPE 等核心大模型下载到正确的文件夹里。如果您在国内网络环境不佳，脚本内包含镜像加速代理)*

---

## 🎮 第三阶段：开始克隆您自己的声音！

环境准备就绪后，您就可以像项目作者一样，炼制属于自己的声音了。

1. **录制声音**：准备 10-30 分钟您自己说话或唱歌的清晰干音（无伴奏），放入 `recordings/raw/` 文件夹。
2. **处理数据**：运行命令清洗并切片您的声音数据：
   ```cmd
   python voice_cover.py make-dataset recordings/raw --name my_voice --trim-silence --denoise
   ```
3. **启动引擎训练**：
   双击运行本项目提供的 `start_applio.cmd`，浏览器会自动打开训练界面。
   * 选择“Train（训练）”标签。
   * 数据集路径填入 `datasets/my_voice/segments`。
   * 设置 200 到 400 轮 (Epochs) 进行训练。
   * 训练完成后，将生成的模型文件从 `C:\Applio\logs` 拷贝到本项目的 `models/my_voice/` 文件夹下。
4. **合成神曲**：
   找一首别人的原唱，通过工具分离出干音，然后在 Applio 推理界面选中您刚练好的 `.pth` 模型，就能把原唱换成您的声音啦！

*(更详细的混合与分离参数，请参考 `README.md`)*
