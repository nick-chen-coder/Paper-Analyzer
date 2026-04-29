import os
import re
import threading
import time
import json
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, Listbox, END, Checkbutton, IntVar, Toplevel, Text, Button, Entry, Label, Frame, StringVar, Radiobutton
from pathlib import Path
import requests
from mineru import MinerU          # 新增 MinerU SDK
import glob                        # 用于查找生成的文件

# ------------------------------------------------------------
# DeepSeek API 配置
# ------------------------------------------------------------
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ------------------------------------------------------------
# 默认提示词（包含标题和内容）
# ------------------------------------------------------------
DEFAULT_PROMPTS = {
    "refs": {
        "title": "核心参考文献",
        "content": """请从以下论文中提取所有参考文献，并识别出其中最重要的文献（通常是被多次引用、经典工作或与本研究高度相关的文献）。按重要性排序，每个文献以“序号. 标题”格式列出，并换行简要介绍该文献的核心贡献。

论文全文：
{pdf_text}"""
    },
    "terms": {
        "title": "关键技术术语",
        "content": """请从以下论文中提取所有专业术语（包括但不限于技术名词、模型名称、方法名称、指标等）。按出现顺序排序，每个术语需提供：
- 中文翻译（如适用）
- 英文原文（必填）
- 术语类型：如果是常规经典术语，注明所属领域（如“机器学习”、“计算机视觉”）；如果是新兴术语（首次在本文或近年提出），注明出自本文哪篇参考文献（用参考文献序号标注）。
输出格式示例：
1. 术语1 (英文) - 中文翻译 - 领域/出处
2. 术语2 (英文) - 中文翻译 - 领域/出处

论文全文：
{pdf_text}"""
    },
    "summary": {
        "title": "论文详细概括",
        "content": """请按照以下结构详细概括这篇论文：

【研究问题】
- 论文试图解决什么核心问题？
- 现有方法存在什么缺陷？

【技术链路】
- 整体框架：输入→处理→输出的完整流程
- 关键技术：使用了什么模型/算法/创新点？
- 技术细节：关键参数、训练方式、优化策略

【实验结果】
- 主要指标：在哪些数据集上测试？达到什么效果？
- 对比结果：相比基线/前人工作提升了多少？
- 消融实验：各模块的贡献度如何？

【结论价值】
- 论文的主要贡献是什么？
- 实际应用价值在哪里？

论文全文：
{pdf_text}"""
    }
}

# ------------------------------------------------------------
# 提示词文件管理（兼容旧格式：字符串自动升级为对象）
# ------------------------------------------------------------
PROMPTS_FILE = "prompts.json"

def load_prompts():
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key in ["refs", "terms", "summary"]:
            if key in data and isinstance(data[key], str):
                data[key] = {
                    "title": DEFAULT_PROMPTS[key]["title"],
                    "content": data[key]
                }
        return data
    else:
        return {k: {"title": v["title"], "content": v["content"]} for k, v in DEFAULT_PROMPTS.items()}

def save_prompts(prompts):
    with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

user_prompts = load_prompts()

# ------------------------------------------------------------
# DeepSeek API 调用
# ------------------------------------------------------------
def call_deepseek_api(api_key, prompt, model, system_message="你是一个专业的学术助手。", max_retries=3):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 8192
    }
    for attempt in range(max_retries):
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                print(f"DeepSeek API 错误 {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"DeepSeek API 调用失败 (尝试 {attempt+1}/{max_retries}): {e}")
            time.sleep(2)
    return None

# ------------------------------------------------------------
# MinerU 转换函数（使用 SDK，输出目录下生成 文件名/full.md）
# ------------------------------------------------------------
def convert_pdf_with_mineru(pdf_path, output_dir, api_token=None, log_func=print):
    """
    调用 MinerU SDK 将 PDF 转换为 Markdown，返回生成的 full.md 绝对路径。
    - 若提供 api_token 则使用精准模式；否则使用 Flash 模式（免费，≤20页）。
    """
    pdf_path = Path(pdf_path)
    pdf_stem = pdf_path.stem
    target_dir = Path(output_dir) / pdf_stem
    target_dir.mkdir(parents=True, exist_ok=True)
    full_md_path = target_dir / "full.md"

    try:
        if api_token and api_token.strip():
            # 精准模式
            log_func(f"  🎯 使用 MinerU 精准模式: {pdf_path.name}")
            client = MinerU(api_token.strip())
            for result in client.extract_batch([str(pdf_path)]):
                # result.filename 一般为不带后缀的文件名
                save_dir = target_dir
                result.save_all(str(save_dir))          # 保存所有输出到该目录
                # 查找生成的 .md 文件并重命名为 full.md
                md_files = glob.glob(os.path.join(str(save_dir), "*.md"))
                if md_files:
                    origin_md = md_files[0]
                    if Path(origin_md) != full_md_path:
                        os.rename(origin_md, str(full_md_path))
                    log_func(f"  ✓ 精准模式完成: {full_md_path}")
                    return str(full_md_path)
                else:
                    log_func("  ✗ 未找到 Markdown 输出文件")
                    return None
        else:
            # Flash 模式（无 token）
            log_func(f"  ⚡ 使用 MinerU Flash 模式（免费）: {pdf_path.name}")
            client = MinerU()
            result = client.flash_extract(str(pdf_path))
            # Flash 模式直接获取 markdown 内容
            with open(full_md_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            log_func(f"  ✓ Flash 模式完成: {full_md_path}")
            return str(full_md_path)
    except Exception as e:
        log_func(f"  ✗ MinerU 转换失败: {e}")
        return None

# ------------------------------------------------------------
# 分析功能（读取 MD 文本）
# ------------------------------------------------------------
def generate_refs_content(api_key, md_text, model, log_func):
    log_func("  → 正在识别重要文献...")
    prompt_template = user_prompts["refs"]["content"]
    prompt = prompt_template.format(pdf_text=md_text)
    result = call_deepseek_api(api_key, prompt, model)
    if result is not None:
        log_func("  ✓ 重要文献生成成功")
    else:
        log_func("  ✗ 重要文献生成失败")
    return result

def generate_terms_content(api_key, md_text, model, log_func):
    log_func("  → 正在提取专业术语...")
    prompt_template = user_prompts["terms"]["content"]
    prompt = prompt_template.format(pdf_text=md_text)
    result = call_deepseek_api(api_key, prompt, model)
    if result is not None:
        log_func("  ✓ 术语提取成功")
    else:
        log_func("  ✗ 术语提取失败")
    return result

def generate_summary_content(api_key, md_text, model, log_func):
    log_func("  → 正在生成论文概括...")
    prompt_template = user_prompts["summary"]["content"]
    prompt = prompt_template.format(pdf_text=md_text)
    result = call_deepseek_api(api_key, prompt, model)
    if result is not None:
        log_func("  ✓ 概括生成成功")
    else:
        log_func("  ✗ 概括生成失败")
    return result

# ------------------------------------------------------------
# 组装并保存 Markdown 报告
# ------------------------------------------------------------
def build_and_save_markdown(pdf_name, output_path, results, options, log_func):
    lines = []
    lines.append(f"# {pdf_name}\n")
    has_content = False

    for key, opt_label in [("refs", "refs"), ("terms", "terms"), ("summary", "summary")]:
        if options.get(opt_label) and results.get(key):
            title = user_prompts[key]["title"]
            lines.append(f"## {title}")
            lines.append(results[key])
            lines.append("")
            has_content = True

    if not has_content:
        log_func("  ⚠ 没有任何分析选项被勾选或生成失败，跳过输出")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if output_path.exists() else "w"
    with open(output_path, mode, encoding='utf-8') as f:
        if mode == "a":
            f.write("\n\n---\n\n")
        f.write("\n".join(lines))

    log_func(f"  ✓ 分析报告已{'追加到' if mode=='a' else '保存至'}: {output_path}")
    return True

# ------------------------------------------------------------
# 使用 Markdown 内容处理单个 PDF
# ------------------------------------------------------------
def process_pdf_with_md(pdf_path, md_path, output_md_path, api_key, model, options, log_func):
    log_func(f"\n开始分析: {pdf_path}")
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception as e:
        log_func(f"  ✗ 无法读取 MD 文件 {md_path}: {e}")
        return

    if not md_text.strip():
        log_func(f"  ✗ MD 文件内容为空，跳过")
        return

    pdf_name = Path(pdf_path).stem
    results = {}
    if options.get("refs"):
        results["refs"] = generate_refs_content(api_key, md_text, model, log_func)
    if options.get("terms"):
        results["terms"] = generate_terms_content(api_key, md_text, model, log_func)
    if options.get("summary"):
        results["summary"] = generate_summary_content(api_key, md_text, model, log_func)

    build_and_save_markdown(pdf_name, output_md_path, results, options, log_func)

# ------------------------------------------------------------
# 提示词编辑窗口
# ------------------------------------------------------------
class PromptEditor:
    def __init__(self, parent):
        self.window = Toplevel(parent)
        self.window.title("编辑提示词（标题 + 内容）")
        self.window.geometry("800x650")

        self.tab_buttons = {}
        self.tab_frames = {}
        self.title_entries = {}
        self.content_texts = {}
        self.current_tab = None

        tab_defs = [
            ("重要文献", "refs"),
            ("专业术语", "terms"),
            ("论文概括", "summary")
        ]

        btn_frame = Frame(self.window)
        btn_frame.pack(fill=tk.X, pady=5)
        for label, key in tab_defs:
            btn = Button(btn_frame, text=label, command=lambda k=key: self.show_tab(k))
            btn.pack(side=tk.LEFT, padx=5)

        container = Frame(self.window)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for label, key in tab_defs:
            frame = Frame(container)
            title_label = Label(frame, text="标题（将作为 Markdown 二级标题）:")
            title_label.pack(anchor=tk.W)
            title_var = StringVar(value=user_prompts[key]["title"])
            title_entry = Entry(frame, textvariable=title_var, width=80)
            title_entry.pack(fill=tk.X, pady=(0,5))
            self.title_entries[key] = title_var

            content_label = Label(frame, text="提示词内容（可用变量：{pdf_text}）:")
            content_label.pack(anchor=tk.W)
            text_widget = Text(frame, wrap=tk.WORD, font=("Consolas", 10))
            text_scroll = tk.Scrollbar(frame, command=text_widget.yview)
            text_widget.configure(yscrollcommand=text_scroll.set)
            text_widget.insert("1.0", user_prompts[key]["content"])
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.content_texts[key] = text_widget

            self.tab_frames[key] = frame

        save_btn = Button(self.window, text="保存修改", command=self.save_prompts)
        save_btn.pack(pady=5)

        self.show_tab("refs")

    def show_tab(self, key):
        if self.current_tab:
            self.current_tab.pack_forget()
        self.current_tab = self.tab_frames[key]
        self.current_tab.pack(fill=tk.BOTH, expand=True)

    def save_prompts(self):
        for key in ["refs", "terms", "summary"]:
            new_title = self.title_entries[key].get().strip()
            new_content = self.content_texts[key].get("1.0", tk.END).strip()
            if not new_title:
                new_title = DEFAULT_PROMPTS[key]["title"]
            if not new_content:
                new_content = DEFAULT_PROMPTS[key]["content"]
            user_prompts[key] = {
                "title": new_title,
                "content": new_content
            }
        save_prompts(user_prompts)
        messagebox.showinfo("提示", "提示词已保存！")

# ------------------------------------------------------------
# 收集文件夹中所有 PDF（递归）
# ------------------------------------------------------------
def collect_pdfs_from_folder(folder_path):
    folder = Path(folder_path)
    pdf_map = {}
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                abs_path = Path(root) / file
                try:
                    rel_path = abs_path.relative_to(folder)
                except ValueError:
                    rel_path = Path(file)
                pdf_map[str(rel_path)] = abs_path
    return pdf_map

# ------------------------------------------------------------
# 构建输出路径映射（用于 DeepSeek 报告）
# ------------------------------------------------------------
def build_job_list(items, output_root):
    jobs = []
    output_root = Path(output_root)

    for typ, path in items:
        if typ == 'file':
            pdf_path = Path(path)
            out_path = output_root / (pdf_path.stem + ".md")
            jobs.append((pdf_path, out_path))
        elif typ == 'folder':
            folder_path = Path(path)
            folder_name = folder_path.name
            pdf_map = collect_pdfs_from_folder(folder_path)
            for rel_pdf, abs_pdf in pdf_map.items():
                rel_md = Path(rel_pdf).with_suffix(".md")
                out_path = output_root / folder_name / rel_md
                jobs.append((abs_pdf, out_path))
    return jobs

# ------------------------------------------------------------
# 主 GUI 应用
# ------------------------------------------------------------
class PaperAnalyzerApp:
    def __init__(self, master):
        self.master = master
        master.title("论文智能分析工具（MinerU + DeepSeek）")
        master.geometry("950x850")

        # ----- DeepSeek API Key -----
        api_frame = Frame(master)
        api_frame.pack(pady=10, padx=10, fill=tk.X)
        Label(api_frame, text="DeepSeek API Key:").pack(side=tk.LEFT)
        self.api_key_var = StringVar()
        self.api_entry = Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_entry.pack(side=tk.LEFT, padx=(10,0), expand=True, fill=tk.X)

        # ----- MinerU API Key (可选，为空则用 Flash 模式) -----
        mineru_api_frame = Frame(master)
        mineru_api_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(mineru_api_frame, text="MinerU API Key (可选):").pack(side=tk.LEFT)
        self.mineru_api_key_var = StringVar()
        self.mineru_api_entry = Entry(mineru_api_frame, textvariable=self.mineru_api_key_var, width=50, show="*")
        self.mineru_api_entry.pack(side=tk.LEFT, padx=(10,0), expand=True, fill=tk.X)

        # ----- MinerU 输出目录 -----
        mineru_out_frame = Frame(master)
        mineru_out_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(mineru_out_frame, text="MinerU 输出目录:").pack(side=tk.LEFT)
        self.mineru_output_dir_var = StringVar()
        self.mineru_out_entry = Entry(mineru_out_frame, textvariable=self.mineru_output_dir_var, width=50)
        self.mineru_out_entry.pack(side=tk.LEFT, padx=(10,0), expand=True, fill=tk.X)
        Button(mineru_out_frame, text="浏览...", command=self.browse_mineru_output).pack(side=tk.LEFT, padx=5)

        # ----- 运行模式 -----
        mode_frame = Frame(master)
        mode_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(mode_frame, text="运行模式:").pack(side=tk.LEFT)
        self.mode_var = StringVar(value="continuous")
        Radiobutton(mode_frame, text="连续模式", variable=self.mode_var, value="continuous").pack(side=tk.LEFT, padx=5)
        Radiobutton(mode_frame, text="检查模式（转换后需手动继续）", variable=self.mode_var, value="check").pack(side=tk.LEFT, padx=5)

        # ----- DeepSeek 模型选择 -----
        model_frame = Frame(master)
        model_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(model_frame, text="选择模型:").pack(side=tk.LEFT)
        self.model_var = StringVar(value="deepseek-v4-flash")
        model_menu = tk.OptionMenu(model_frame, self.model_var, "deepseek-v4-flash", "deepseek-v4-pro")
        model_menu.pack(side=tk.LEFT, padx=(10,0))

        # ----- 输出根目录 (DeepSeek 分析报告) -----
        out_frame = Frame(master)
        out_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(out_frame, text="输出根目录:").pack(side=tk.LEFT)
        self.output_dir_var = StringVar()
        self.out_entry = Entry(out_frame, textvariable=self.output_dir_var, width=50)
        self.out_entry.pack(side=tk.LEFT, padx=(10,0), expand=True, fill=tk.X)
        Button(out_frame, text="浏览...", command=self.browse_output).pack(side=tk.LEFT, padx=5)

        # ----- 添加文件 / 文件夹 -----
        add_frame = Frame(master)
        add_frame.pack(pady=5, padx=10, fill=tk.X)
        Button(add_frame, text="添加 PDF 文件", command=self.add_pdf_files).pack(side=tk.LEFT, padx=5)
        Button(add_frame, text="添加文件夹", command=self.add_folder).pack(side=tk.LEFT, padx=5)
        Button(add_frame, text="移除选中项", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        Button(add_frame, text="清空列表", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # ----- 输入列表 -----
        list_frame = Frame(master)
        list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        Label(list_frame, text="已添加的文件/文件夹:").pack(anchor=tk.W)
        self.listbox = Listbox(list_frame, height=8, selectmode=tk.EXTENDED)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        # ----- 分析选项 -----
        options_frame = Frame(master)
        options_frame.pack(pady=5, padx=10, fill=tk.X)
        Label(options_frame, text="分析选项:").pack(side=tk.LEFT)
        self.refs_var = IntVar()
        self.terms_var = IntVar()
        self.summary_var = IntVar()
        Checkbutton(options_frame, text="识别重要文献", variable=self.refs_var).pack(side=tk.LEFT, padx=5)
        Checkbutton(options_frame, text="提取专业术语", variable=self.terms_var).pack(side=tk.LEFT, padx=5)
        Checkbutton(options_frame, text="详细概括论文", variable=self.summary_var).pack(side=tk.LEFT, padx=5)

        # ----- 操作按钮 -----
        btn_frame = Frame(master)
        btn_frame.pack(pady=5)
        self.start_btn = Button(btn_frame, text="开始分析", command=self.start_analysis)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.continue_btn = Button(btn_frame, text="▶ 继续分析", command=self.continue_analysis, state=tk.DISABLED)
        self.continue_btn.pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="修改提示词", command=self.edit_prompts).pack(side=tk.LEFT, padx=5)

        # ----- 日志区域 -----
        self.log_text = scrolledtext.ScrolledText(master, wrap=tk.WORD, height=15)
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # ----- 状态栏 -----
        self.status_var = StringVar()
        self.status_label = Label(master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 内部数据
        self.items = []
        self.analysis_jobs = []
        self.pdf_to_md = {}
        self.cur_mode = "continuous"

    def browse_mineru_output(self):
        path = filedialog.askdirectory(title="选择 MinerU 输出目录")
        if path:
            self.mineru_output_dir_var.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="选择输出根目录")
        if path:
            self.output_dir_var.set(path)

    def add_pdf_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for f in files:
            abs_path = os.path.abspath(f)
            if ('file', abs_path) not in self.items:
                self.items.append(('file', abs_path))
                self.listbox.insert(END, f"[文件] {abs_path}")

    def add_folder(self):
        folder = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if folder:
            abs_path = os.path.abspath(folder)
            if ('folder', abs_path) not in self.items:
                self.items.append(('folder', abs_path))
                self.listbox.insert(END, f"[目录] {abs_path}")

    def remove_selected(self):
        selected = self.listbox.curselection()
        if not selected:
            return
        for i in sorted(selected, reverse=True):
            del self.items[i]
            self.listbox.delete(i)

    def clear_all(self):
        self.items.clear()
        self.listbox.delete(0, END)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.master.update_idletasks()

    def edit_prompts(self):
        PromptEditor(self.master)

    def start_analysis(self):
        if not self.items:
            messagebox.showwarning("提示", "请至少添加一个 PDF 文件或文件夹")
            return
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请输入 DeepSeek API Key")
            return
        mineru_api_key = self.mineru_api_key_var.get().strip()   # 可为空
        mineru_output_dir = self.mineru_output_dir_var.get().strip()
        if not mineru_output_dir:
            messagebox.showwarning("提示", "请选择 MinerU 输出目录")
            return
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出根目录")
            return
        if not (self.refs_var.get() or self.terms_var.get() or self.summary_var.get()):
            messagebox.showwarning("提示", "请至少选择一个分析选项")
            return

        self.cur_mode = self.mode_var.get()

        try:
            self.analysis_jobs = build_job_list(self.items, output_dir)
        except Exception as e:
            messagebox.showerror("错误", f"构建任务列表失败: {e}")
            return

        if not self.analysis_jobs:
            messagebox.showinfo("提示", "没有找到任何 PDF 文件")
            return

        self.start_btn.config(state=tk.DISABLED)
        self.continue_btn.config(state=tk.DISABLED)

        pdf_list = list(set([job[0] for job in self.analysis_jobs]))

        threading.Thread(target=self.mineru_conversion_worker, args=(mineru_api_key, mineru_output_dir, pdf_list), daemon=True).start()

    def mineru_conversion_worker(self, mineru_api_key, mineru_output_dir, pdf_list):
        self.log("\n========== 开始 MinerU 转换 ==========")
        self.pdf_to_md.clear()
        for pdf_path in pdf_list:
            self.log(f"转换: {pdf_path}")
            md_path = convert_pdf_with_mineru(
                str(pdf_path), mineru_output_dir,
                api_token=mineru_api_key,
                log_func=self.log
            )
            if md_path:
                self.pdf_to_md[str(pdf_path)] = md_path
            else:
                self.log(f"  ✗ 跳过该文件（转换失败）")
        self.log("========== MinerU 转换全部完成 ==========\n")

        if self.cur_mode == "continuous":
            self.log("连续模式：自动开始 DeepSeek 分析...")
            self.start_deepseek_analysis()
        else:
            self.master.after(0, self.show_continue_button)

    def show_continue_button(self):
        self.continue_btn.config(state=tk.NORMAL)
        self.log("检查模式：MinerU 转换已完成，请检查 MD 文件，点击“继续分析”开始 DeepSeek 分析。")
        self.status_var.set("MinerU 转换完成，请点击“继续”按钮")

    def continue_analysis(self):
        self.continue_btn.config(state=tk.DISABLED)
        self.status_var.set("正在进行 DeepSeek 分析...")
        threading.Thread(target=self.start_deepseek_analysis, daemon=True).start()

    def start_deepseek_analysis(self):
        api_key = self.api_key_var.get().strip()
        selected_model = self.model_var.get()
        options = {
            "refs": bool(self.refs_var.get()),
            "terms": bool(self.terms_var.get()),
            "summary": bool(self.summary_var.get())
        }

        valid_jobs = []
        for pdf_path, out_path in self.analysis_jobs:
            pdf_str = str(pdf_path)
            if pdf_str in self.pdf_to_md:
                valid_jobs.append((pdf_str, self.pdf_to_md[pdf_str], out_path))
            else:
                self.log(f"  ⚠ 跳过 {pdf_path}（未成功转换为 Markdown）")

        total = len(valid_jobs)
        self.log(f"\n========== 开始 DeepSeek 分析，共 {total} 个文件 ==========")
        for idx, (pdf_path, md_path, out_path) in enumerate(valid_jobs, 1):
            self.log(f"\n--------- [{idx}/{total}] {pdf_path} ---------")
            try:
                process_pdf_with_md(pdf_path, md_path, out_path, api_key, selected_model, options, self.log)
            except Exception as e:
                self.log(f"  ✗ 处理失败: {e}")

        self.log("\n✅ 所有论文处理完成！")
        self.start_btn.config(state=tk.NORMAL)
        self.status_var.set("就绪")

def main():
    root = tk.Tk()
    app = PaperAnalyzerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()