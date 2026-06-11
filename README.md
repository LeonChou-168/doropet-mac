<div align="center">

<img src="opendoro/data/icons/app.ico" alt="DoroPet Logo" width="100" height="100"/>

# DoroPet

### 你的智能桌面伴侣

[![Version](https://img.shields.io/badge/version-3.6.4-blue.svg)](https://gitee.com/waterfeet/DoroPet_V3/releases)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

集 Live2D 桌宠、AI 对话、语音交互、养成系统、Galgame 叙事、音乐播放器于一体的桌面应用

[English](README_EN.md)

</div>

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

**系统要求**：Windows 10/11 64 位，4GB 内存，OpenGL 3.0+

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

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。
