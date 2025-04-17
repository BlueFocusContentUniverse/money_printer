# MoneyPrinterPlus 项目交接

一个基于AI的自动化视频生成与发布系统，专注于汽车领域高效内容生产和多平台分发。

## 1. 项目概述

### 1.1 核心功能
- 基于AI自动生成视频脚本与内容
- 支持多种AI语音合成与音效处理
- 自动匹配视频素材与脚本内容
- 智能添加字幕、贴图和特效
- 多平台自动化发布（抖音、快手、小红书等）
- 任务队列管理与自动重试机制

### 1.2 技术架构
- **Python 3.10**: 主要开发语言
- **Streamlit**: 用户界面框架
- **Celery**: 分布式任务队列系统，处理异步视频生成任务
- **Redis**: 作为Celery的消息代理和结果后端
- **MySQL**: 关系型数据库，存储任务和用户数据
- **MinIO**: 对象存储服务，管理视频和音频资源
- **FFmpeg**: 视频处理核心引擎
- **多种AI模型集成**: 支持OpenAI、百度千帆、阿里通义、DeepSeek等LLM服务

### 1.3 系统架构
- **前端层**: Streamlit界面，用于任务创建和管理
- **任务调度层**: Celery工作队列负责任务调度和执行
- **服务层**: 模块化服务组件，处理各类专业功能
- **资源管理层**: MinIO对象存储，负责素材和成品管理
- **数据持久层**: MySQL数据库，存储任务状态和用户配置

## 2. 完整目录结构

```
moneyprinter3/
├── bgmusic/                 # 背景音乐资源
├── common/                  # 公共模块
│   ├── cache/               # 缓存处理
│   └── config/              # 配置文件处理
│       ├── config.py        # 配置管理类
│       ├── config.yml       # 主配置文件
│       └── config.example.yml # 配置示例
├── data/                    # 数据管理模块
│   ├── data_base_manager.py # 数据库管理
│   └── minio_handler.py     # MinIO对象存储处理
├── final/                   # 最终视频输出目录
│   └── videos/              # 视频分类目录
├── fonts/                   # 字体资源
│   └── WenYue_XinQingNianTi*.otf # 文悦新青年体等字体
├── locales/                 # 本地化文件
│   ├── zh-CN.json           # 中文本地化
│   └── en.json              # 英文本地化
├── pages/                   # Streamlit应用页面
│   ├── common.py            # 页面公共组件
│   └── 02_merge_video.py    # 任务看版页面
├── screenshots/             # 截图临时目录
├── services/                # 核心服务模块
│   ├── audio/               # 音频处理服务
│   │   ├── audio_service.py # 音频服务基类
│   │   ├── chattts_service.py # ChatTTS服务
│   │   ├── chattts_enhanced_service.py # 增强版ChatTTS服务
│   │   ├── fish_audio_service.py # FishAudio服务
│   │   ├── fish_whisper.py # Fish语音识别服务
│   │   ├── gptsovits_service.py # GPTSoVITS服务
│   │   ├── faster_whisper_recognition_service.py # 快速Whisper识别
│   │   ├── whisper.py      # Whisper语音转文字服务
│   │   ├── flash_recognizer.py # 语音识别服务
│   │   └── tts_audio_editor.py # 音频编辑工具
│   ├── captioning/          # 字幕生成服务
│   │   ├── captioning_service.py # 字幕服务
│   │   ├── caption_from_text_audio.py # 文本音频生成字幕
│   │   └── whisper_caption.py # Whisper字幕生成
│   ├── hunjian/             # 混剪服务
│   │   └── hunjian_service.py # 混剪服务实现
│   ├── llm/                 # 大语言模型集成
│   │   ├── llm_provider.py  # LLM提供商管理
│   │   ├── llm_service.py   # LLM服务基类
│   │   ├── openai_service.py # OpenAI服务
│   │   ├── azure_service.py # Azure OpenAI服务
│   │   ├── baidu_qianfan_service.py # 百度千帆服务
│   │   ├── baichuan_service.py # 百川大模型服务
│   │   ├── tongyi_service.py # 阿里通义服务
│   │   ├── deepseek_service.py # DeepSeek服务
│   │   ├── kimi_service.py  # 月之暗面Kimi服务
│   │   └── ollama_service.py # 本地Ollama服务
│   ├── material_process/    # 素材处理服务
│   │   ├── material_processor.py # 素材处理器
│   │   ├── overlay_analyzer.py # 叠加层分析器(处理贴图)
│   │   ├── overlay_processor.py # 叠加层处理器
│   │   ├── overlay_image.py # 图像叠加工具
│   │   ├── screenshot.py    # 截图处理
│   │   ├── sound_effect_analyzer.py # 音效分析器
│   │   └── sound_effect_process.py # 音效处理器
│   ├── publisher/           # 发布服务
│   │   ├── publisher_base.py # 发布服务基类
│   │   ├── douyin_publisher.py # 抖音发布服务
│   │   ├── kuaishou_publisher.py # 快手发布服务
│   │   ├── xiaohongshu_publisher.py # 小红书发布服务
│   │   └── shipinhao_publisher.py # 视频号发布服务
│   ├── resource/            # 资源管理服务
│   │   ├── pexels_service.py # Pexels视频资源服务
│   │   └── pixabay_service.py # Pixabay视频资源服务
│   └── video/               # 视频处理服务
│       ├── video_service.py  # 视频服务(核心实现)
│       ├── merge_service.py  # 视频合并服务
│       └── texiao_service.py # 视频特效服务
├── sounds/                  # 音效资源目录
│   ├── 叮.mp3               # 提示音效
│   ├── 噔噔.mp3             # 转场音效
│   ├── 哇哦.mp3             # 惊叹音效
│   └── ...                  # 其他音效
├── tools/                   # 工具函数模块
│   ├── file_utils.py        # 文件处理工具
│   ├── font_utils.py        # 字体处理工具
│   ├── sys_utils.py         # 系统相关工具
│   ├── tr_utils.py          # 翻译工具
│   ├── utils.py             # 通用工具函数
│   └── windows_to_linux.py  # 路径转换工具
├── worker/                  # Celery工作进程
│   ├── celery.py            # Celery任务定义
│   ├── celeryconfig.py      # Celery配置
│   ├── start_celery.py      # Celery启动脚本
│   ├── task_record_manager.py # 任务记录管理
│   └── work/                # 任务工作目录(临时文件)
├── gui.py                   # 主GUI配置界面
├── main.py                  # 主应用入口
└── requirements.txt         # 项目依赖
```

## 3. 核心模块详解

### 3.1 配置系统 (common/config)

位于`common/config`目录，负责项目全局配置管理：

- **config.py**: 配置管理类，处理配置的加载、验证和保存
- **config.yml**: 主配置文件，包含以下关键配置区域:
  - `audio`: 音频服务配置
  - `llm`: 大语言模型配置
  - `resource`: 资源服务配置
  - `publisher`: 发布平台配置
  - `minio_config`: MinIO对象存储配置
  - `paths`: 关键路径配置

#### 配置示例
```yaml
# Audio相关配置
audio:
  provider: fish_audio  # 默认音频服务提供商
  fish_audio:
    api_key: "xxxxxxxx"  # Fish Audio API密钥
  local_tts:
    ChatTTS_Enhanced:
      server_location: http://xxx.xxx.xxx.xxx:7870  # ChatTTS增强版服务地址

# 大模型配置
llm:
  provider: OpenAI  # 默认LLM提供商
  OpenAI:
    api_key: "sk-xxxxxxxx"
    base_url: "https://xxx.xxx.xxx/v1/"
    model_name: "gpt-3.5-turbo"

# 资源获取配置  
resource:
  provider: pexels
  pexels:
    api_key: "xxxxxxxx"

# 路径配置
paths:
  tag_mappings_path: /path/to/tag_mappings.json
  permanent_storage_dir: /path/to/storage
  sound_dir: /path/to/sounds
```

### 3.2 Celery任务系统 (worker/)

位于`worker`目录，负责异步任务管理：

#### 核心组件

- **celery.py**: 定义主要任务类和任务函数，包括：
  - `VideoGenerationTask`: 视频生成基础任务类
  - `generate_video_task`: 视频生成主任务
  - `scan_and_process_ready_tasks`: 扫描任务定时器
  - `retry_failed_tasks`: 失败任务重试定时器

- **celeryconfig.py**: Celery配置，包含：
  - 队列配置：高优先级、默认、低优先级
  - Redis连接配置
  - Worker配置参数
  - 定时任务调度配置

- **task_record_manager.py**: 负责任务状态记录和管理

#### 任务处理流程

1. **任务获取**: 从数据库获取任务参数
2. **任务初始化**: 创建工作目录、更新任务状态
3. **标签提取**: 通过LLM从脚本中提取标签
4. **音频生成**: 根据脚本生成TTS音频
5. **音效处理**: 分析脚本并添加音效
6. **视频选择**: 根据脚本匹配视频素材
7. **视频处理**: 生成和处理视频片段
8. **合成处理**: 合并音频、视频并添加贴图
9. **生成字幕**: 识别音频生成字幕并添加
10. **视频归档**: 生成最终视频并存储到MinIO

### 3.3 音频处理服务 (services/audio)

提供多种文本转语音和语音识别服务：

#### 主要服务类

- **ChatTTSService**: 本地ChatTTS服务，提供基础语音合成
- **ChatTTSEnhancedService**: 增强版ChatTTS，支持更多风格和控制
- **GPTSoVITSService**: 支持声音克隆和更自然的语音合成
- **FishAudioService**: FishAudio API集成，高质量云端TTS服务
- **FishSpeechRecognizer/WhisperService**: 语音识别服务，用于自动字幕

#### 关键配置

音频服务的配置参数在`config.yml`的`audio`部分，包括：
```yaml
audio:
  provider: fish_audio  # 当前使用的主TTS服务
  local_tts:
    provider: ChatTTS_Enhanced  # 本地TTS使用的服务
    ChatTTS_Enhanced:
      server_location: http://xxx.xxx.xxx.xxx:7870
  fish_audio:
    api_key: "xxxxxxxx"
```

### 3.4 视频处理服务 (services/video)

负责视频片段处理、合成和特效：

#### 主要服务类

- **VideoService**: 核心视频处理类，提供全面的视频处理功能
  - 视频剪辑、拼接和转场效果
  - 视频格式转换和尺寸调整
  - 字幕和水印添加
  - 背景音乐处理

- **VideoMixService**: 处理视频混剪，根据音频内容匹配视频片段

- **MergeService**: 视频合并服务，处理多段视频的合并和转场

#### 关键功能

```python
# 视频归一化处理
normalize_video_list = video_service.normalize_video()

# 添加贴图/字幕/音频
processed_path = processor.process(video_info['path'], time_range)

# 生成带音频的最终视频
video_file = video_service.generate_video_with_audio()
```

### 3.5 素材处理服务 (services/material_process)

处理视频附加元素，如贴图、音效等：

#### 主要组件

- **OverlayAnalyzer**: 分析脚本，识别需要添加贴图的位置
- **OverlayProcessor**: 在视频上添加贴图
- **ScreenshotHandler**: 处理截图和图像获取
- **SoundEffectAnalyzer**: 分析脚本中的音效标记
- **SoundEffectProcessor**: 处理和添加音效

#### 脚本标记语法

- 贴图标记: `[I-关键词]内容[/I]`
- 音效标记: `[S-音效类型]音效名称[/S]`

### 3.6 LLM服务 (services/llm)

集成多种大语言模型，处理内容生成：

#### 支持的模型列表

- OpenAI (GPT-3.5/4)
- 微软Azure OpenAI
- 百度千帆 (文心一言)
- 阿里通义千问
- DeepSeek AI
- 百川大模型
- 月之暗面Kimi
- 本地部署的Ollama模型

#### 主要用途

- 脚本生成与内容优化
- 标签提取和分类
- 贴图和音效分析
- 内容总结和转写

### 3.7 发布服务 (services/publisher)

支持多平台视频发布：

#### 支持的平台

- 抖音
- 快手
- 小红书
- 视频号(微信)

#### 发布流程

1. 初始化浏览器会话
2. 登录目标平台
3. 上传视频文件
4. 设置标题、描述和标签
5. 提交发布请求
6. 监控发布状态

### 3.8 数据管理模块 (data/)

负责数据的存储和检索：

#### 主要组件

- **data_base_manager.py**: MySQL数据库管理
  - 任务状态记录
  - 用户数据管理
  - 任务查询和统计

- **minio_handler.py**: MinIO对象存储处理
  - 视频和音频文件存储
  - 文件访问URL生成
  - 存储配额和权限管理

## 4. 主要工作流程详解

### 4.1 视频生成工作流

1. **任务创建**:
   - 用户通过页面设置任务参数(脚本、音频风格等)
   - 参数保存到数据库并提交到任务队列

2. **脚本处理**:
   - 使用LLM服务分析脚本内容
   - 提取关键词和标签
   - 生成格式化的脚本片段

3. **音频生成**:
   - 将脚本传入TTS服务生成语音
   - 分析脚本中的音效标记
   - 添加音效到适当位置

4. **视频素材匹配**:
   - 基于脚本内容选择匹配的视频素材
   - 处理视频时长以匹配音频
   - 视频片段提取和归一化

5. **视频合成**:
   - 分析脚本中的贴图标记
   - 添加贴图到适当位置
   - 合并音频和视频
   - 添加字幕和特效

6. **存储和分发**:
   - 生成最终视频文件
   - 上传到MinIO存储
   - 存储路径和URL记录到数据库
   - 可选择发布到多平台

### 4.2 任务状态流转

- **ready**: 任务创建并等待处理
- **processing**: 任务正在处理中
- **success**: 任务处理成功
- **failure**: 任务处理失败
- **retry**: 任务等待重试

## 5. 环境配置与部署

### 5.1 依赖安装

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装系统依赖
# Ubuntu/Debian
apt-get update
apt-get install -y ffmpeg fonts-noto-cjk

# CentOS/RHEL
yum install -y ffmpeg
```

### 5.2 配置文件

1. 复制示例配置文件:
   ```bash
   cp common/config/config.example.yml common/config/config.yml
   ```

2. 编辑配置文件，填入必要的API密钥和服务参数:
   - LLM服务API密钥
   - 音频服务API密钥
   - 资源服务API密钥
   - 路径配置
   - MinIO配置

### 5.3 数据库配置

```bash
# MySQL数据库初始化
mysql -u root -p < docs/setup/init_db.sql
```

### 5.4 启动服务

1. **启动Redis服务**:
   ```bash
   redis-server --port 6381
   ```

2. **启动Celery Worker和Beat**:
   ```bash
   cd /path/to/moneyprinter3
   python worker/start_celery.py
   ```

3. **启动Web界面**:
   ```bash
   streamlit run gui.py
   ```

### 5.5 服务端口

- **Streamlit界面**: 默认8501端口
- **Redis**: 6381端口
- **Celery Flower监控**: 5555端口 (可选)

## 6. 常见问题与故障排查

### 6.1 任务卡住不执行

- 检查Redis连接是否正常: `redis-cli -p 6381 ping`
- 检查Celery Worker状态: `celery -A worker.celery status`
- 检查任务日志: `tail -f worker/celery.log`

### 6.2 音频生成失败

- 检查TTS服务连接: 测试对应的音频服务API
- 验证API密钥是否有效
- 检查脚本格式是否正确

### 6.3 视频处理失败

- 检查FFmpeg安装: `ffmpeg -version`
- 确认视频素材路径正确
- 检查磁盘空间是否充足

### 6.4 绝对路径问题

项目中存在一些硬编码的绝对路径，在`common/config/config.yml`的`paths`部分统一配置:

```yaml
paths:
  tag_mappings_path: /path/to/tag_mappings.json
  permanent_storage_dir: /path/to/storage
  sound_dir: /path/to/sounds
```

### 6.5 日志路径

- Celery主日志: `worker/celery.log`
- 任务状态记录: 数据库task_records表

## 7. 代码维护注意事项

### 7.1 硬编码路径问题

项目中部分模块还存在硬编码路径，主要集中在:

1. `worker/celery.py` - 部分路径和API参数
2. `services/material_process/overlay_analyzer.py` - 代理设置
3. `services/material_process/screenshot.py` - 服务URL

建议优先修复这些硬编码问题，将所有配置集中到config.yml中管理。

### 7.2 API密钥管理

目前API密钥直接存储在配置文件中，建议:

1. 使用环境变量替代配置文件存储敏感信息
2. 实现密钥管理服务，避免明文存储
3. 对接企业密钥管理系统

### 7.3 模型切换机制

当前模型切换时需要修改配置文件，建议:

1. 实现动态模型切换接口
2. 添加模型自动选择逻辑
3. 完善模型失败后的自动降级机制

## 8. 后续开发计划

### 8.1 短期优化

- 解决硬编码路径问题
- 完善错误处理机制
- 优化资源利用率
- 提高视频生成质量

### 8.2 长期规划

- 实现更智能的视频内容分析
- 优化视频素材匹配算法
- 支持更多AI模型和语音服务
- 增强跨平台发布能力

## 9. 联系与支持


