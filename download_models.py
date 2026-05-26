import os
import urllib.request
import sys

# 针对国内网络环境，默认使用 HuggingFace 的国内镜像加速节点
HF_MIRROR = "https://hf-mirror.com/"

# 核心底模下载列表（格式：文件目标路径 : 文件的 HuggingFace 原始相对链接）
# 这里我们假设 Applio 安装在 C:\Applio
APPLIO_BASE_DIR = r"C:\Applio"

MODELS_TO_DOWNLOAD = {
    # 1. 核心特征提取器 (Hubert)
    os.path.join(APPLIO_BASE_DIR, "rvc", "models", "hubert", "hubert_base.pt"): 
        "lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt",
    
    # 2. 音高预测模型 (RMVPE)
    os.path.join(APPLIO_BASE_DIR, "rvc", "models", "predictors", "rmvpe.pt"): 
        "lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt",
    
    # 3. RVC v2 训练用的基础底模 (VITS D 和 G 模型，40k 采样率)
    os.path.join(APPLIO_BASE_DIR, "rvc", "models", "pretrain", "f0D40k.pth"): 
        "lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0D40k.pth",
    os.path.join(APPLIO_BASE_DIR, "rvc", "models", "pretrain", "f0G40k.pth"): 
        "lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0G40k.pth"
}

def download_file(url, destination):
    # 确保目标文件夹存在
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    if os.path.exists(destination):
        print(f"[跳过] 文件已存在: {destination}")
        return

    print(f"\n[下载中] 开始下载: {os.path.basename(destination)}")
    print(f"来源链接: {url}")
    
    try:
        # 使用 urlretrieve 下载并显示简单进度
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, int(downloaded * 100 / total_size))
                sys.stdout.write(f"\r进度: {percent}%  ({downloaded/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB)")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, destination, progress)
        print(f"\n[完成] 成功保存到: {destination}")
    except Exception as e:
        print(f"\n[失败] 下载出错: {e}")
        print("请检查网络连接或尝试开启/关闭全局代理。")

def main():
    print("==================================================")
    print("    🚀 AI 声音克隆系统 - 底模一键下载脚本")
    print("==================================================")
    print("本脚本将自动从 HuggingFace 国内镜像源下载训练所需的必备大模型。\n")
    
    if not os.path.exists(APPLIO_BASE_DIR):
        print(f"⚠️  警告: 未检测到 Applio 目录 ({APPLIO_BASE_DIR})。")
        print("请先按照 SETUP_GUIDE.md 下载并解压 Applio 到 C 盘根目录！")
        choice = input("是否仍要下载并强行创建目录？(y/n): ")
        if choice.lower() != 'y':
            print("下载已取消。")
            return

    for dest_path, hf_rel_path in MODELS_TO_DOWNLOAD.items():
        # 拼接镜像下载链接
        full_url = HF_MIRROR + hf_rel_path
        download_file(full_url, dest_path)
        
    print("\n🎉 全部底模处理完毕！您可以按照 SETUP_GUIDE.md 的说明继续操作了。")

if __name__ == "__main__":
    main()
