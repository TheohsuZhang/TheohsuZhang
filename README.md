# command_Backup

## 简介 (Introduction)
这是一个专为汽车电子自动化测试台架（如 Vector CANoe, CANape, INCA 等环境）设计的数据文件自动抓取与备份工具。

在自动化测试序列（如 JScript/VBScript 控制的用例）执行过程中，它能够以极高的频率监控并抓取生成的测量数据文件（默认 `.mf4` 格式），自动添加时间戳前缀并转移到备份目录，从而防止测试数据被后续序列覆盖或丢失。

## 主要功能 (Features)
- **文件监控与搬运**：毫秒级监控源目录，发现目标文件（如 `.mf4`）立即重命名并移动。
- **自动重命名防冲突**：自动为转移的文件添加 `YYYYMMDD-HHMMSS_` 时间戳前缀。
- **安全机制**：自动忽略正在生成的 `.tmp` 临时文件；自动检测并关闭冲突的旧实例，确保单例运行。
- **灵活配置**：通过 `config.ini` 配置源目录、目标目录、扫描频率、超时时间等。
- **双模式运行**：支持单次扫描模式和持续监控（超时自动退出）模式。

## ⚠️ 重要：Windows 7 兼容性与打包指南 (Windows 7 Compatibility)

在工业测试台架中，经常会遇到运行老旧 Windows 7 (特别是 32 位) 系统的上位机。如果在这些机器上运行较高版本 Python (如 3.9+) 打包的程序，会出现 `api-ms-win-core-path-l1-1-0.dll is missing` 的报错。

为了解决此问题，请遵循以下打包规范：

### 推荐方案：使用 Python 3.8 打包
**Python 3.8 是最后一个官方支持 Windows 7 的版本。**
1. 在开发机上安装 **Python 3.8 (32-bit / x86)** 环境。
2. 在该环境中执行 `pip install pyinstaller` 安装打包依赖。
3. 运行项目提供的 `build_all.py` 或 `build_one.py` 进行编译。
这样编译出的 `command_Backup-x86.exe` 即可在老旧的 Win7 测试台架上原生完美运行。

### 备选方案：DLL 补丁 (免重新编译)
如果暂且无法降级 Python 重新编译，可以下载兼容补丁：
1. 从开源社区（例如 GitHub: `nalexandru/api-ms-win-core-path-HACK`）下载对应架构（x86）的 `api-ms-win-core-path-l1-1-0.dll` 文件。
2. 将该 DLL 文件**直接放置在与 `command_Backup-x86.exe` 同级的目录中**即可启动。

## 配置说明 (`config.ini`)
程序启动时会自动读取同目录下的 `config.ini` 文件，典型配置如下：
```ini
[paths]
source_dir = E:\Zhangxiaoxu\JScript\111         # 自动化脚本生成数据的目录
backup_dir = E:\Zhangxiaoxu\JScript\111\backup  # 数据备份目标目录
file_extensions = .mf4                          # 要抓取的文件后缀 (多为 ASAM MDF4)
time_range_minutes = 5                          # 仅抓取最近 5 分钟修改的文件 (0 为不限制)
scan_delay_seconds = 2                          # 启动后延迟 2 秒开始扫描
monitor_timeout_seconds = 30                    # 监控模式超时时间 (30 秒未抓到文件则自动退出)
monitor_interval_seconds = 0.5                  # 扫描间隔时间 (每 0.5 秒轮询一次)
```

## 编译与构建 (Build Instructions)
本项目包含严谨的构建脚本，支持多架构并行打包以适配不同台架：
- `build_config.ini`：在这里配置你电脑上 32位和 64位 Python 解释器的绝对路径。
- `build_all.py`：多架构打包编排器。读取配置并自动生成 `-x86.exe` 和 `-x64.exe`，输出到 `release/` 目录。
- `build.py`：单文件快速构建工具，并在打包时自动递增代码中的 Patch 版本号和更新日期。