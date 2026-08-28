围棋训练助手 — 使用说明
========================

【这是什么】
一个 Windows 桌面围棋软件：你和 KataGo AI 对弈，每一步都会实时显示
当前局面胜率最高的几个点位（Top5，带胜率数字）、最佳点高亮，以及整盘胜率曲线。

【怎么启动】
方式一（推荐）：到本仓库 Releases 页面下载完整 Windows 版压缩包（含 KataGo 引擎），解压后双击 围棋训练助手.exe
方式二：从源码运行：先运行 setup.bat 创建虚拟环境，把引擎文件放入 engine_bin\ 目录（见下方【引擎下载】），再双击 run.bat

【引擎下载】（仅源码运行需要；Releases 完整版已内置）
1. 下载 KataGo 引擎，解压出 katago.exe：
   https://github.com/lightvector/KataGo/releases/download/v1.18.1/katago-v1.18.1-opencl-windows-x64.zip
2. 下载权重文件 b18c384nbt-uec.bin.gz：
   https://github.com/lightvector/KataGo/releases/download/v1.12.4/b18c384nbt-uec.bin.gz
3. 把 katago.exe 和 b18c384nbt-uec.bin.gz 放到 engine_bin\ 目录

【怎么玩】
- 默认你执黑、AI 执白，点击棋盘交叉点落子
- 右侧面板：
  · AI 强度：快速 / 标准 / 深度（影响每一步分析时间与精度）
  · 悔棋：撤销上一手（可连续撤销）
  · 停一手：不落子让 AI 继续（双方各停一手则对局结束，由 KataGo 判胜负）
  · 认输
  · 新局·执黑 / 新局·执白
  · 导出 SGF：保存棋谱，可用任意围棋软件复盘
- 顶部菜单：对局（新局/悔棋/停一手/认输/导出SGF）、设置（9/13/19 路棋盘）

【AI 强度参考】（RTX 4060 级别，标准约 0.7 秒/步）
- 快速 200 visits：约 0.3 秒，适合日常随手练
- 标准 600 visits：约 0.7 秒，推荐
- 深度 1600 visits：约 2 秒，接近最强，适合复盘验证

【技术信息】
- 引擎：KataGo v1.18.1（OpenCL，走 GPU）+ b18c384nbt-uec 权重
- 界面：Python + PySide6（Qt6）
- 规则：自研规则引擎（含吃子/打劫/超劫/自杀判定，13 项单元测试）

【常见问题】
1. 打开后提示"引擎启动失败"？
   - 检查显卡驱动是否支持 OpenCL（NVIDIA 驱动自带，一般没问题）
   - 确认 engine_bin 目录里有 katago.exe 和 b18c384nbt-uec.bin.gz
2. 每一步很慢？
   - 在右侧把 AI 强度调成"快速"
   - 确认引擎状态显示"引擎就绪 ✓"（说明在用 GPU）
3. 想复盘别人的棋谱？用"导出 SGF"保存，或用菜单"设置"切换棋盘大小。

【项目结构】
- main.py            程序入口
- app/board/         围棋规则引擎（棋盘/规则/对局）
- app/engine/        KataGo 进程通信 + 分析解析
- app/ui/            界面（棋盘绘制/胜率曲线/主窗口）
- app/utils/sgf.py   SGF 棋谱导出
- config/            设置与 KataGo 配置
- engine_bin/        KataGo 引擎与权重
- tests/             单元测试（pytest tests）
