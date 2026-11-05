> [!IMPORTANT]
> **本仓库是 DoroPet 的 macOS Apple Silicon 移植版（非官方）**
>
> 本仓库是上游 [DoroPet_V3](https://gitee.com/waterfeet/DoroPet_V3) 的 macOS Apple Silicon（`arm64`）社区移植，由 [LeonChou-168](https://github.com/LeonChou-168) 维护，**并非上游官方版本**。
> 上游的 **Python 版已停止维护**（详见下文「关于上游版本状态」）；如需获取最新版，请使用上游 Rust 版。
> macOS 的安装、运行与打包说明见 **[opendoro/README_MACOS.md](opendoro/README_MACOS.md)**。

<div align="center">

<img src="opendoro/data/icons/app.ico" alt="DoroPet Logo" width="100" height="100"/>

# DoroPet

### 你的智能桌面伴侣

### macOS Apple Silicon 移植版（非官方）

---

[![Version](https://img.shields.io/badge/version-3.6.8-blue.svg)](https://gitee.com/waterfeet/DoroPet_V3/releases)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20arm64%20%7C%20Windows-lightgrey.svg)](opendoro/README_MACOS.md)

集 Live2D 桌宠、AI 对话、语音交互、养成系统、Galgame 叙事、音乐播放器于一体的桌面应用

[English](README_EN.md)

</div>

---

## 关于上游版本状态

> [!NOTE]
> **停止更新的是上游的 Python 版，不是本 macOS 移植。**
>
> 上游作者 waterfeet 已停止维护 DoroPet_V3 的 Python 版本，转向 Rust 版本。想获取最新版 DoroPet，请前往上游 Rust 版发布页：[RUST版本DoroPet](https://gitee.com/waterfeet/doropetrelease/releases)。
> 本仓库是社区维护的 macOS 移植分支，会尽量跟随上游同步；但上游 Python 版不会再新增功能。

**上游作者原话（开发者说明）**：

> 这个版本本身功能已经不再稳定，下载后可能无法运行。本人没有精力再维护这个项目，后续只会更新rust的版本。有兴趣可以Fork后自己去修改。无法打开的话，可以让本地的代码agent尝试修复，一般情况下只是依赖库的问题，修改依赖库配置，或者改动少量源码就能跑起来。

---

## 这个仓库做了什么

本仓库基于上游 DoroPet_V3 **3.6.8**，在保留上游功能与资源的前提下增加了 **macOS Apple Silicon（arm64）适配**：

- **macOS 启动与安装脚本**：`opendoro/scripts/setup_macos.sh` 创建 `.venv-macos`（Python 3.11/3.12 arm64）并安装 macOS 依赖；`opendoro/scripts/run_macos.sh` 设置 Qt / UTF-8 环境变量后启动；`opendoro/DoroPet.command` 支持在访达中双击启动。
- **PyInstaller 打包**：`opendoro/scripts/build_macos_app.sh` + `opendoro/packaging/macos/DoroPet.spec` 生成 `dist/DoroPet.app`（arm64，含 `NSMicrophoneUsageDescription` 等 Info.plist 配置；产物未签名，仅供本地使用）。
- **macOS 依赖调整**：`opendoro/requirements-macos.txt` 排除 Windows 专用的 `pyaudiowpatch`（WASAPI 回环），补充 `pyobjc-framework-Cocoa`、`pyinstaller` 以及 3.6.x 需要的 `pydantic-ai`、`playwright` 等依赖。
- **macOS 数据目录与权限**：运行时数据保存在应用包外的 `~/Library/Application Support/DoroPet`、`~/Library/Logs/DoroPet`、`~/Library/Caches/DoroPet`；语音与唤醒词功能需要麦克风权限（系统设置 → 隐私与安全性 → 麦克风）。
- **音乐播放后端**：默认使用 Qt Multimedia；检测到 `/Applications/VLC.app` 或 Homebrew VLC 时启用可选的 VLC 后端，未安装则记录警告并回退。
- **兼容上游**：保留 Windows `.bat` 启动脚本、Windows DLL、VLC 二进制与 Live2D 资源，便于继续与上游合并；Windows 用户仍可按下方「快速开始」使用。
- **注意**：不要在 macOS 上使用上游的自动更新，它会用 Windows 构建覆盖当前代码；请手动同步 `upstream` 后重新应用 macOS 补丁。

### macOS 快速开始

```bash
git clone https://github.com/LeonChou-168/doropet-mac.git
cd doropet-mac/opendoro

./scripts/setup_macos.sh    # 首次运行：创建 .venv-macos 并安装 macOS 依赖
./scripts/run_macos.sh      # 启动 DoroPet

./scripts/build_macos_app.sh && open dist/DoroPet.app   # 可选：打包 .app
```

> 更完整的说明（系统要求、数据目录、麦克风权限、VLC、构建与签名注意事项）见 **[opendoro/README_MACOS.md](opendoro/README_MACOS.md)**。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 🎭 **Live2D 桌宠** | 流畅角色渲染，支持表情切换、动作播放、鼠标追踪、边缘吸附、随机溜达 |
| 🤖 **AI 对话** | 支持 OpenAI / DeepSeek / Gemini / Claude / Ollama 等 8+ 模型，流式输出、多会话管理 |
| 🎙️ **语音交互** | 唤醒词"Hey Doro"检测 + 语音识别 + 多引擎 TTS 合成 |
| 🎮 **养成系统** | 饱食度 / 心情 / 清洁度 / 能量四大属性，可投喂、玩耍、清洁、互动 |
| 📖 **Galgame 叙事** | AI 驱动互动故事，好感度 / 多结局 / 存档读档 / 背包商店 / 事件触发 |
| 🎵 **音乐播放器** | 多平台搜索，VLC 引擎播放，歌词同步，频谱特效，歌单管理 |
| 🔌 **Agent 技能** | AI 可调用搜索/文件/图片生成等工具，支持自定义技能扩展 |
| 🧠 **智能记忆** | AI 自动分析消息重要性，提取长期记忆，让对话更连贯 |
| 👤 **角色扮演** | 自定义 AI 人格设定，可绑定 Live2D 模型 |
| 🎨 **明暗主题** | 明暗双主题切换，字体缩放适配 |

---

## 截图

<table>
  <tr>
    <td align="center"><b>🖥️ 桌面宠物</b></td>
    <td align="center"><b>💬 智能对话</b></td>
    <td align="center"><b>📊 主页状态</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/doro.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/智能对话.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/主页.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>⚙️ 设置界面</b></td>
    <td align="center"><b>🤖 模型配置</b></td>
    <td align="center"><b>🎭 Live2D 配置</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/设置界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/模型配置.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/live2d.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎙️ 语音配置</b></td>
    <td align="center"><b>🧠 记忆管理</b></td>
    <td align="center"><b>💬 沉浸聊天</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/语音配置界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/记忆管理.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/沉浸聊天.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎵 音乐播放器</b></td>
    <td align="center"><b>📖 小说生成器</b></td>
    <td align="center"><b>👤 人格提示词</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/音乐播放器界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/小说生成器.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/人格提示词.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎨 Agent 技能</b></td>
    <td align="center"><b>🔄 更新界面</b></td>
    <td align="center"><b>📱 右键菜单</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/agent-skill.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/更新界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/右键菜单.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🐭 鼠标追逐</b></td>
    <td align="center"><b>🔌 插件演示</b></td>
    <td align="center"><b>📋 运行日志</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/鼠标追逐.gif" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/插件演示.gif" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/logpage.png" width="280"/></td>
  </tr>
</table>

---

## 快速开始

> 以下为上游原版的 Windows 运行方式；macOS Apple Silicon 用户请使用上方「[这个仓库做了什么](#这个仓库做了什么)」中的 macOS 快速开始，完整说明见 [opendoro/README_MACOS.md](opendoro/README_MACOS.md)。

**系统要求（Windows）**：Windows 10/11 64 位，4GB 内存，OpenGL 3.0+

### 方式一：下载发行版（推荐）

1. 前往 [Releases 页面](https://gitee.com/waterfeet/DoroPet_V3/releases) 下载最新压缩包
2. 解压后双击 `install_env.bat` 自动安装环境
3. 安装完成后双击 `start_app.bat` 启动

### 方式二：源码运行

```bash
git clone https://gitee.com/waterfeet/DoroPet_V3.git
cd DoroPet_V3
pip install -r requirements.txt
python opendoro/main.py
```

首次启动后，在"模型配置"页面添加 API Key 即可开始使用。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| GUI | PyQt5 + PyQt-Fluent-Widgets |
| Live2D | live2d-py + OpenGL v3 |
| AI | OpenAI SDK 兼容多提供商 |
| 语音 | sherpa-onnx + edge-tts |
| 音乐 | VLC + musicdl |
| 数据库 | SQLite |

---

## 署名 / Attribution

- **上游项目**：[waterfeet](https://gitee.com/waterfeet) / [DoroPet_V3](https://gitee.com/waterfeet/DoroPet_V3) — DoroPet 的原作者与原始 Python 版项目，采用 [Apache License 2.0](LICENSE)；上游 Python 版已停止更新，作者转向 Rust 版（[发布页](https://gitee.com/waterfeet/doropetrelease/releases)）。
- **macOS 移植维护**：[LeonChou-168](https://github.com/LeonChou-168) — macOS Apple Silicon 适配、PyInstaller 打包与持续维护。
- 本仓库为社区移植项目（非官方），与上游作者无从属关系；上游代码与资源的版权归原作者及贡献者所有。

## 开源协议

本项目沿用上游的 [Apache License 2.0](LICENSE) 开源。你可以自由使用、修改和分发，但需保留原始版权与许可声明（详见 [LICENSE](LICENSE)）。
