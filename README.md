# 📄 Paper Analyzer — 论文智能分析工具

**一键将 PDF 论文转化为结构化分析报告**

一个基于 **MinerU PDF 识别** + **DeepSeek 大模型** 的桌面端论文阅读辅助工具。  
自动提取核心参考文献、专业术语并生成详细概括，大幅提升文献阅读效率。

---

## ✨ 功能亮点

- 🔍 **三大分析模块**
  - **核心参考文献**：自动识别最相关/引用最多的文献
  - **关键技术术语**：英中对照 + 领域/出处标注
  - **论文详细概括**：研究问题、技术链路、实验结果、结论价值
- 📂 **批量处理**：支持单个 PDF 或整个文件夹（含子目录）
- 🧠 **智能 Markdown 转换**：基于 MinerU 的 PDF → Markdown（保留标题、表格、LaTeX 公式等结构）
- ⚡ **双模式运行**
  - `连续模式`：转换后自动调用 DeepSeek 分析
  - `检查模式`：转换后可先核对 Markdown，再手动启动分析
- 🖥️ **直观 GUI**：使用 Tkinter 构建，无需命令行知识
- 💾 **结果持久化**：分析报告输出为 `.md` 文件，支持追加保存
- 🔧 **可自定义提示词**：内置编辑器，可调整每个模块的提示词和标题

---

## 🧩 工作流程

```
PDF 文件/文件夹
    │
    ▼
MinerU (Flash/精准模式)
    │
    ▼
高质量 Markdown (.md)
    │
    ▼
DeepSeek 分析 (参考文献、术语、概括)
    │
    ▼
结构化分析报告 (.md)
```

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖库（详见 requirements.txt）

### 安装步骤

1. **克隆仓库**
   ```
   git clone https://github.com/yourname/paper-analyzer.git
   cd paper-analyzer
   ```

2. **安装依赖**
   ```
   pip install -r requirements.txt
   ```
   其中 `mineru` 为 MinerU 官方 Python SDK，请确保已正确安装。

3. **准备 API 密钥**

   - **DeepSeek API Key**：[申请地址](https://platform.deepseek.com/)
   - **MinerU API Token（可选）**：[申请地址](https://mineru.net/)  
     *留空则自动使用免费 Flash 模式（单文件 ≤20 页），否则使用精准模式。*

4. **运行程序**
   ```
   python main.py
   ```

---

## 🕹️ 使用方法

1. **填写密钥**
   - 输入 DeepSeek API Key
   - 可选输入 MinerU API Token

2. **设置目录**
   - `MinerU 输出目录`：存放 PDF 转换后的 Markdown（按 PDF 名称生成子文件夹，内含 `full.md`）
   - `输出根目录`：DeepSeek 分析报告的保存位置

3. **添加文件**
   - 点击「添加 PDF 文件」选择单个或多个 PDF
   - 或点击「添加文件夹」批量导入整个目录

4. **选择分析选项**
   - 勾选所需模块：参考文献 / 术语 / 概括

5. **选择模式**
   - `连续模式`：一键到底，自动分析
   - `检查模式`：MinerU 转换后暂停，手动检查 MD 文件后再点击「继续分析」

6. **点击「开始分析」**
   - 日志区域会显示实时进度，完成后报告自动保存。

---

## ⚙️ 自定义提示词

内置提示词编辑器，可随时调整分析内容和输出标题：

- 点击「修改提示词」
- 分别编辑「重要文献」「专业术语」「论文概括」三个标签页
- 使用变量 `{pdf_text}` 代表论文全文
- 保存后立即生效

提示词会存储在 `prompts.json` 中，方便版本管理或团队共享。

---

## 📦 打包为独立 EXE

如果你需要将程序打包成一个可执行文件（方便分享给未安装 Python 的用户），可使用 PyInstaller。

确保已安装 PyInstaller：
```
pip install pyinstaller
```

然后在项目目录下执行以下命令（**以模块方式运行，不添加图标，输出文件名为“论文分析工具”**）：

```
python -m PyInstaller --onefile -w --name "论文分析工具" main.py
```

- `--onefile`：打包为单个 EXE 文件
- `-w`：隐藏控制台窗口（GUI 程序推荐）
- `--name`：指定输出文件名（不含 .exe 后缀，会自动补充）
- 未使用 `-i`，所以使用默认图标

打包完成后，EXE 文件位于 `dist/` 文件夹内。  
如果运行时提示缺少 `mineru` 等模块，可添加隐藏导入参数：
```
python -m PyInstaller --onefile -w --name "论文分析工具" --hidden-import mineru main.py
```

---

## 📁 项目结构

```
paper-analyzer/
├── main.py              # 主程序（GUI + 逻辑）
├── prompts.json         # 提示词配置（自动生成）
├── requirements.txt     # 依赖列表
└── README.md            # 本文件
```

---

## 🧪 依赖说明

| 库 | 用途 |
|----|------|
| `tkinter` | GUI 界面 |
| `requests` | HTTP 请求（DeepSeek API） |
| `mineru` | MinerU Python SDK（PDF 转 Markdown） |
| `glob` | 文件查找（辅助 MinerU 结果处理） |
| `json` | 配置读写 |
| `threading` | 后台任务处理 |

---

## 📌 注意事项

- **MinerU Flash 模式**免费使用，但每个 PDF 不得超过 20 页；精准模式需 API Token，支持最长 200 页。
- 程序会将 PDF 文件名作为标题写入报告，建议 PDF 命名规范。
- Markdown 中的图片链接不会传递给 DeepSeek（LLM 无法识别图像内容），模型仅根据上下文理解。
- 若打包为 exe 出现模块缺失，请添加 `--hidden-import mineru` 等参数。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！  
你可以：
- 报告 bug 或提出功能建议
- 添加新的分析模块（如翻译、图表解释）
- 优化界面或性能

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源，可自由使用、修改和分发。

---

**如果这个工具对你有帮助，请给一个 ⭐ Star 支持一下！**