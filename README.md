# Command Backup Utility

**版本 (Version)**: v1.1.4
**更新日期 (Date)**: 2026-03-10

## 📖 简介 (Introduction)

`command_Backup` 是一个专为汽车电子自动化测试台架（如 Vector CANoe, CANape, INCA 等环境）设计的数据文件自动抓取与备份工具。

在自动化测试序列（如 JScript/VBScript 控制的用例）执行过程中，它能够以极高的频率监控并抓取生成的测量数据文件（默认 `.mf4` 格式），自动添加时间戳前缀并转移到备份目录，从而防止测试数据被后续序列覆盖或丢失。

## ✨ 主要功能 (Features)

*   **⚡ 极速文件搬运**：毫秒级监控源目录，发现目标文件（如 `.mf4`）立即处理。
*   **🕒 智能重命名**：
    *   自动为文件添加 `YYYYMMDD-HHMMSS_` 时间戳前缀，防止同名覆盖。
    *   支持命令行传入自定义前缀（如测试用例 ID）。
*   **🛡️ 安全机制**：
    *   **临时文件过滤**：自动忽略正在写入的 `.tmp` 文件，防止移动不完整的数据。
    *   **单例保护**：启动时自动检测并关闭旧的程序实例，确保系统中只有一个“守门员”在运行。
*   **⚙️ 灵活配置**：
    *   所有行为通过 `config.ini` 控制，无需修改代码。
    *   支持**双模式运行**：单次扫描（用完即走）或 持续监控（守护进程）。
*   **🖥️ Windows 7 兼容**：特别优化构建流程，完美支持老旧的 x86 Windows 7 测试台架。

## 🛑 严格的文件过滤与命名规范 (Strict File Filtering)

为了应对环境复杂的自动化测试台架（如意外中断、软件崩溃产生的畸形文件），本工具引入了**极严苛的文件过滤机制**。只有完全健康的有效文件才会被转移，任何疑似损坏或未完成的文件都将被原地拦截。

### ✅ 允许抓取的健康文件（命名要求）：
- 必须严格匹配配置的后缀名（如 `.mf4`）。
- 文件名**仅允许**包含：**英文字母、数字、下划线 `_`、减号 `-`、空格、小括号 `()`**。
- 文件大小必须 **严格大于 0 字节**。
- 示例：`J310R_2026-03-17_0001.mf4`, `test_data (1).mf4`, `Case-A.mf4`

### ❌ 将被直接拒绝的异常/畸形文件（不予备份）：
1. **0 字节空壳文件**：因测试台架软件中断或死循环生成的 `0 KB` 废弃文件。
2. **包含多个点号 (`.`)**：如 `J310R.part2.mf4` 或隐藏文件 `.hidden.mf4`（一个文件只能有 1 个用于后缀的点）。
3. **包含临时关键字**：文件名中任何位置包含 `tmp` 或 `temp`（不区分大小写，如 `data.temp.mf4`）。
4. **双重/多重后缀重叠**：如 `data.mf4.mf4`，或者与其他后缀/时间戳混合 `test.mf4.2026-03.mf4`。
5. **包含非法/特殊字符**：包含中文、逗号 `,`、井号 `#`、`&` 或其他系统不可见乱码字符。

## 🚀 快速开始 (Quick Start)

### 1. 运行 (Run)
双击 `command_Backup.exe` 即可运行。它会自动读取同目录下的 `config.ini`。

### 2. 配置 (Configuration)
编辑 `config.ini` 文件来调整行为：

```ini
[paths]
# 监听的源目录（自动化脚本生成数据的目录）
source_dir = E:\TestBench\Data\Source

# 备份的目标目录（数据将被移动到这里）
backup_dir = E:\TestBench\Data\Backup

# 要抓取的文件后缀 (逗号分隔，默认为 .mf4)
file_extensions = .mf4, .dat

# [可选] 仅抓取最近 N 分钟内修改的文件 (0 = 不限制)
time_range_minutes = 5

# [可选] 启动后延迟 N 秒再开始扫描 (用于等待文件写入完成)
scan_delay_seconds = 2

# [可选] 监控模式超时时间 (秒)
# 0 = 单次扫描模式 (运行一次即退出)
# >0 = 持续监控模式 (直到 N 秒内没有新文件或时间耗尽)
monitor_timeout_seconds = 30

# [可选] 扫描间隔 (秒)
monitor_interval_seconds = 0.5
```

### 3. 命令行参数 (Advanced Usage)
支持通过命令行传递参数作为文件名前缀：

```powershell
# 此时生成的文件名为: 20260316-080000_TestCase001_data_1.mf4
command_Backup.exe "TestCase001"
```

## ⚠️ Windows 7 兼容性说明 (Compatibility)

工业现场常存在老旧的 Windows 7 32位系统。为确保兼容性，**必须遵循以下规则**：

1.  **推荐方案**：使用 **Python 3.8 (x86)** 进行打包。Python 3.8 是最后一个官方支持 Win7 的版本。
2.  **构建结果**：使用项目提供的构建脚本生成的 `command_Backup-x86.exe` 可直接在 Win7 上运行。
3.  **常见报错**：若在 Win7 上运行高版本 Python 打包的程序，会报错 `api-ms-win-core-path-l1-1-0.dll is missing`。

## 🛠️ 开发与构建 (Build Instructions)

本项目内置了自动化的构建系统，基于 `PyInstaller`。

### 依赖准备
请确保安装了依赖：
```bash
pip install pyinstaller
```

### 构建脚本

| 脚本 | 用途 | 说明 |
| :--- | :--- | :--- |
| `build.py` | **日常开发构建** | 使用当前环境 Python 打包。会自动增加 Patch 版本号并更新日期。 |
| `build_all.py` | **发布版本构建** | **(推荐)** 读取 `build_config.ini`，调用指定路径的 32位和 64位 Python 分别打包，生成最终发布文件。 |
| `build_one.py` | **单架构构建** | 底层构建工具，支持 `--no-bump` 参数防止版本号跳变。 |

### 如何发布新版本
1.  配置 `build_config.ini`，填入你电脑上 Python x86 和 x64 的解释器路径。
2.  运行构建命令：
    ```powershell
    python build_all.py
    ```
3.  在 `release/` 目录下即可找到 `command_Backup-x86.exe` 和 `command_Backup-x64.exe`。

## 📂 项目结构 (Project Structure)

*   `command_Backup.py`: 核心源代码。
*   `config.ini`: 默认配置文件。
*   `build_all.py` / `build.py`: 构建脚本。
*   `.github/copilot-instructions.md`: GitHub Copilot 的辅助开发指南。

---
*Created for Automotive Test Automation*
