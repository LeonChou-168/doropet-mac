<div align="center">

<img src="opendoro/data/icons/app.ico" alt="DoroPet Logo" width="100" height="100"/>

# DoroPet

### Your Smart Desktop Companion

[![Version](https://img.shields.io/badge/version-3.6.4-blue.svg)](https://gitee.com/waterfeet/DoroPet_V3/releases)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

A desktop app integrating Live2D pet, AI chat, voice interaction, pet simulation, Galgame storytelling, and music player — all in one place

[中文文档](README.md)

</div>

---

## Features

| Feature | Description |
|---------|-------------|
| 🎭 **Live2D Pet** | Smooth character rendering with expressions, motion, mouse tracking, edge docking, random wandering |
| 🤖 **AI Chat** | Supports OpenAI / DeepSeek / Gemini / Claude / Ollama, streaming output, multi-session management |
| 🎙️ **Voice** | Wake word "Hey Doro" detection + ASR + multi-engine TTS synthesis |
| 🎮 **Pet Simulation** | Hunger / Mood / Cleanliness / Energy attributes — feed, play, clean, interact |
| 📖 **Galgame** | AI-driven interactive stories, affection system, multiple endings, save/load, inventory, events |
| 🎵 **Music Player** | Multi-platform search, VLC playback, synchronized lyrics, spectrum effects, playlists |
| 🔌 **Agent Skills** | AI can search, browse, generate images, manipulate files — extensible with custom skills |
| 🧠 **Memory** | AI auto-analyzes message importance, extracts long-term memories for coherent conversations |
| 👤 **Role Play** | Custom AI persona (System Prompt), bindable to Live2D models |
| 🎨 **Themes** | Dark & light themes with adjustable font scaling |

---

## Screenshots

<table>
  <tr>
    <td align="center"><b>🖥️ Desktop Pet</b></td>
    <td align="center"><b>💬 AI Chat</b></td>
    <td align="center"><b>📊 Pet Status</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/doro.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/智能对话.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/主页.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>⚙️ Settings</b></td>
    <td align="center"><b>🤖 Model Config</b></td>
    <td align="center"><b>🎭 Live2D Config</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/设置界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/模型配置.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/live2d.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎙️ Voice Config</b></td>
    <td align="center"><b>🧠 Memory Manager</b></td>
    <td align="center"><b>💬 Immersive Chat</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/语音配置界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/记忆管理.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/沉浸聊天.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎵 Music Player</b></td>
    <td align="center"><b>📖 Novel Generator</b></td>
    <td align="center"><b>👤 Role Prompt</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/音乐播放器界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/小说生成器.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/人格提示词.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎨 Agent Skills</b></td>
    <td align="center"><b>🔄 Updates</b></td>
    <td align="center"><b>📱 Context Menu</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/agent-skill.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/更新界面.png" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/右键菜单.png" width="280"/></td>
  </tr>
  <tr>
    <td align="center"><b>🐭 Mouse Chase</b></td>
    <td align="center"><b>🔌 Plugins</b></td>
    <td align="center"><b>📋 Logs</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/鼠标追逐.gif" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/插件演示.gif" width="280"/></td>
    <td><img src="opendoro/data/resourse/img/logpage.png" width="280"/></td>
  </tr>
</table>

---

## Quick Start

**Requirements**: Windows 10/11 64-bit, 4GB RAM, OpenGL 3.0+

### Method 1: Download Release (Recommended)

1. Get the latest ZIP from the [Releases Page](https://gitee.com/waterfeet/DoroPet_V3/releases)
2. Extract, then double-click `install_env.bat` to auto-setup
3. Double-click `start_app.bat` to launch

### Method 2: Run from Source

```bash
git clone https://gitee.com/waterfeet/DoroPet_V3.git
cd DoroPet_V3
pip install -r requirements.txt
python opendoro/main.py
```

After first launch, go to "Model Config" to add your API Key and start using.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | PyQt5 + PyQt-Fluent-Widgets |
| Live2D | live2d-py + OpenGL v3 |
| AI | OpenAI SDK (multi-provider) |
| Voice | sherpa-onnx + edge-tts |
| Music | VLC + musicdl |
| Database | SQLite |

---

## License

This project is licensed under the [MIT License](LICENSE).
