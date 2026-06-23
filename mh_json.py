"""
JSON 层级可视化工具
用法: python json_tree_viewer.py
功能:
  - 粘贴嵌套 JSON → 自动逐层展开 + 解码 JWT
  - 左侧: 可折叠树状图，一眼看清层级
  - 右侧: 完整美化 JSON 输出
  - 底部: 点击节点查看完整值
  - 零依赖，Python 3 自带 tkinter
"""
import json
import base64
import tkinter as tk
from tkinter import ttk, scrolledtext


# ============================================================
# 国际化
# ============================================================

LANG = {
    "zh": {
        "title": "JSON 层级可视化",
        "toolbar_label": "粘贴 JSON →",
        "btn_parse": "解析",
        "btn_clear": "清空",
        "btn_expand": "展开全部",
        "btn_collapse": "折叠全部",
        "btn_copy": "复制美化 JSON",
        "btn_paste": "从剪贴板粘贴",
        "btn_lang": "EN",
        "input_label": "输入（粘贴 JSON）:",
        "tree_label": "树状图（可展开/折叠）:",
        "tree_col_key": "节点",
        "tree_col_val": "值 → 点击查看完整值",
        "detail_label": "选中节点完整值（点击树节点查看）",
        "output_label": "美化 JSON（完整输出）:",
        "status_ready": "就绪 — 粘贴 JSON 后点「解析」",
        "status_empty": "❌ 输入为空",
        "status_parse_err": "❌ JSON 解析失败: ",
        "status_success": "✅ 解析成功 — 点击左侧节点查看完整值",
        "status_copied": "✅ 已复制美化 JSON 到剪贴板",
        "status_nocopy": "⚠️ 没有内容可复制",
        "status_pasted": "已粘贴剪贴板内容，点「解析」查看",
        "status_clip_fail": "❌ 剪贴板为空或不可读",
        "status_cleared": "已清空",
        "obj_summary": "对象, {len} 个键",
        "list_summary": "列表, {len} 项",
        "json_expanded": "[JSON 字符串 → 已展开]",
        "json_fail": "[JSON 解析失败]",
        "jwt_decoded": "[JWT → 已解码]",
        "jwt_label": "JWT, {len} 字符",
        "null_val": "null",
    },
    "en": {
        "title": "JSON Tree Viewer",
        "toolbar_label": "Paste JSON →",
        "btn_parse": "Parse",
        "btn_clear": "Clear",
        "btn_expand": "Expand All",
        "btn_collapse": "Collapse All",
        "btn_copy": "Copy Formatted",
        "btn_paste": "Paste from Clipboard",
        "btn_lang": "中文",
        "input_label": "Input (paste JSON):",
        "tree_label": "Tree (expand/collapse):",
        "tree_col_key": "Node",
        "tree_col_val": "Value → Click node for full detail",
        "detail_label": "Full Value (click tree node to view)",
        "output_label": "Formatted JSON:",
        "status_ready": "Ready — paste JSON and click Parse",
        "status_empty": "❌ Input is empty",
        "status_parse_err": "❌ JSON parse error: ",
        "status_success": "✅ Parsed successfully — click a node to view full value",
        "status_copied": "✅ Formatted JSON copied to clipboard",
        "status_nocopy": "⚠️ Nothing to copy",
        "status_pasted": "Pasted from clipboard, click Parse",
        "status_clip_fail": "❌ Clipboard empty or unreadable",
        "status_cleared": "Cleared",
        "obj_summary": "object, {len} keys",
        "list_summary": "array, {len} items",
        "json_expanded": "[JSON string → expanded]",
        "json_fail": "[JSON parse failed]",
        "jwt_decoded": "[JWT → decoded]",
        "jwt_label": "JWT, {len} chars",
        "null_val": "null",
    },
}


def t(key, lang="zh", **fmt):
    """取翻译文本, fmt 可选格式化"""
    s = LANG.get(lang, LANG["zh"]).get(key, key)
    if fmt:
        s = s.format(**fmt)
    return s


# ============================================================
# 核心解析逻辑
# ============================================================

def is_json_string(s):
    if not isinstance(s, str):
        return False
    s = s.strip()
    if not (s.startswith("{") or s.startswith("[")):
        return False
    try:
        json.loads(s)
        return True
    except Exception:
        return False


def is_jwt(s):
    if not isinstance(s, str):
        return False
    parts = s.split(".")
    return len(parts) == 3 and all(p for p in parts)


def decode_jwt_payload(s):
    try:
        payload = s.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


# ============================================================
# 构建树 + 递归解析
# ============================================================

def build_tree(tree_widget, parent_id, key, val, data_store, lang="zh", max_depth=10, _depth=0):
    """
    递归构建 ttk.Treeview 节点
    自动展开 JSON 字符串、JWT、嵌套 dict/list
    data_store: dict, 存 node_id → 完整值（用于点击查看）
    """
    if _depth >= max_depth:
        return

    label = str(key) if key is not None else "(root)"

    if isinstance(val, dict):
        node = tree_widget.insert(parent_id, "end", text=label,
                                   values=(t("obj_summary", lang, len=len(val)),))
        data_store[node] = json.dumps(val, indent=2, ensure_ascii=False)
        for k, v in val.items():
            build_tree(tree_widget, node, k, v, data_store, lang, max_depth, _depth + 1)

    elif isinstance(val, list):
        node = tree_widget.insert(parent_id, "end", text=label,
                                   values=(t("list_summary", lang, len=len(val)),))
        data_store[node] = json.dumps(val, indent=2, ensure_ascii=False)
        for i, item in enumerate(val):
            build_tree(tree_widget, node, f"[{i}]", item, data_store, lang, max_depth, _depth + 1)

    elif is_json_string(val):
        try:
            decoded = json.loads(val)
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=(t("json_expanded", lang),))
            data_store[node] = json.dumps(decoded, indent=2, ensure_ascii=False)
            items = decoded.items() if isinstance(decoded, dict) else enumerate(decoded)
            for k, v in items:
                key_label = k if isinstance(decoded, dict) else f"[{k}]"
                build_tree(tree_widget, node, key_label, v, data_store, lang, max_depth, _depth + 1)
        except Exception:
            node = tree_widget.insert(parent_id, "end", text=label,
                               values=(t("json_fail", lang),))
            data_store[node] = val

    elif is_jwt(val):
        decoded = decode_jwt_payload(val)
        if decoded:
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=(t("jwt_decoded", lang),))
            data_store[node] = json.dumps(decoded, indent=2, ensure_ascii=False)
            for k, v in decoded.items():
                build_tree(tree_widget, node, k, v, data_store, lang, max_depth, _depth + 1)
        else:
            node = tree_widget.insert(parent_id, "end", text=label,
                               values=(t("jwt_label", lang, len=len(val)),))
            data_store[node] = val

    elif isinstance(val, str):
        s = val.replace("\n", "\\n").replace("\t", "\\t")
        node = tree_widget.insert(parent_id, "end", text=label,
                           values=(s,))
        data_store[node] = val

    elif val is None:
        node = tree_widget.insert(parent_id, "end", text=label, values=(t("null_val", lang),))
        data_store[node] = "null"

    else:
        node = tree_widget.insert(parent_id, "end", text=label, values=(str(val),))
        data_store[node] = str(val)


# ============================================================
# 单个标签页
# ============================================================

class JsonTab:
    """一个标签页：包含输入、树状图、详情、美化输出"""
    def __init__(self, parent, lang, app):
        self.app = app
        self.lang = lang
        self.parsed_data = None
        self.node_data = {}

        main_pane = ttk.PanedWindow(parent, orient="horizontal")
        main_pane.pack(fill="both", expand=True)

        # -- 左栏 --
        left_pane = ttk.PanedWindow(main_pane, orient="vertical")
        main_pane.add(left_pane, weight=1)

        # 输入框
        input_frame = ttk.Frame(left_pane)
        self.lbl_input = ttk.Label(input_frame, text=t("input_label", lang), anchor="w")
        self.lbl_input.pack(fill="x", padx=4, pady=(4, 0))
        input_inner = ttk.Frame(input_frame)
        input_inner.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        self.input_box = tk.Text(input_inner, wrap="none", font=("Consolas", 10), height=6, undo=True)
        in_sy = ttk.Scrollbar(input_inner, orient="vertical", command=self.input_box.yview)
        in_sx = ttk.Scrollbar(input_inner, orient="horizontal", command=self.input_box.xview)
        self.input_box.configure(yscrollcommand=in_sy.set, xscrollcommand=in_sx.set)
        self.input_box.grid(row=0, column=0, sticky="nsew")
        in_sy.grid(row=0, column=1, sticky="ns"); in_sx.grid(row=1, column=0, sticky="ew")
        input_inner.rowconfigure(0, weight=1); input_inner.columnconfigure(0, weight=1)
        left_pane.add(input_frame, weight=1)

        # 树状图
        tree_frame = ttk.Frame(left_pane)
        self.lbl_tree = ttk.Label(tree_frame, text=t("tree_label", lang), anchor="w")
        self.lbl_tree.pack(fill="x", padx=4, pady=(0, 0))
        tree_inner = ttk.Frame(tree_frame)
        tree_inner.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        self.tree = ttk.Treeview(tree_inner, columns=("value",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text=t("tree_col_key", lang))
        self.tree.heading("value", text=t("tree_col_val", lang))
        self.tree.column("#0", width=260, stretch=True)
        self.tree.column("value", width=320, stretch=True)
        tr_sy = ttk.Scrollbar(tree_inner, orient="vertical", command=self.tree.yview)
        tr_sx = ttk.Scrollbar(tree_inner, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tr_sy.set, xscrollcommand=tr_sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tr_sy.grid(row=0, column=1, sticky="ns"); tr_sx.grid(row=1, column=0, sticky="ew")
        tree_inner.rowconfigure(0, weight=1); tree_inner.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_node_select)
        left_pane.add(tree_frame, weight=3)

        # 详情
        self.detail_frame = ttk.LabelFrame(left_pane, text=t("detail_label", lang), padding=(4, 2))
        self.detail_box = scrolledtext.ScrolledText(self.detail_frame, height=4, wrap="word",
                                                      font=("Consolas", 10), bg="#fffff0")
        self.detail_box.pack(fill="both", expand=True)
        left_pane.add(self.detail_frame, weight=1)

        # -- 右栏 --
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        self.lbl_output = ttk.Label(right_frame, text=t("output_label", lang), anchor="w")
        self.lbl_output.pack(fill="x", padx=4, pady=(4, 0))
        out_inner = ttk.Frame(right_frame)
        out_inner.pack(fill="both", expand=True, padx=4, pady=(2, 2))
        self.output_box = tk.Text(out_inner, wrap="none", font=("Consolas", 10), bg="#f5f5f5", undo=True)
        out_sy = ttk.Scrollbar(out_inner, orient="vertical", command=self.output_box.yview)
        out_sx = ttk.Scrollbar(out_inner, orient="horizontal", command=self.output_box.xview)
        self.output_box.configure(yscrollcommand=out_sy.set, xscrollcommand=out_sx.set)
        self.output_box.grid(row=0, column=0, sticky="nsew")
        out_sy.grid(row=0, column=1, sticky="ns"); out_sx.grid(row=1, column=0, sticky="ew")
        out_inner.rowconfigure(0, weight=1); out_inner.columnconfigure(0, weight=1)

    def _on_node_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        full_value = self.node_data.get(item, "")
        self.detail_box.delete("1.0", "end")
        if full_value:
            node_text = self.tree.item(item, "text")
            self.detail_box.insert("1.0", f"# {node_text}\n\n{full_value}")

    def parse(self):
        raw = self.input_box.get("1.0", "end-1c").strip()
        if not raw:
            return False, t("status_empty", self.lang)
        try:
            self.parsed_data = json.loads(raw)
        except json.JSONDecodeError as e:
            return False, t("status_parse_err", self.lang) + str(e)

        self.tree.delete(*self.tree.get_children())
        self.output_box.delete("1.0", "end")
        self.detail_box.delete("1.0", "end")
        self.node_data = {}

        if isinstance(self.parsed_data, dict):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(t("obj_summary", self.lang, len=len(self.parsed_data)),))
            self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
            for key, val in self.parsed_data.items():
                build_tree(self.tree, root_node, key, val, self.node_data, self.lang)
            self.tree.item(root_node, open=True)
        elif isinstance(self.parsed_data, list):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(t("list_summary", self.lang, len=len(self.parsed_data)),))
            self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
            for i, item in enumerate(self.parsed_data):
                build_tree(self.tree, root_node, f"[{i}]", item, self.node_data, self.lang)
            self.tree.item(root_node, open=True)

        formatted = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
        self.output_box.insert("1.0", formatted)
        return True, t("status_success", self.lang)

    def clear(self):
        self.input_box.delete("1.0", "end")
        self.tree.delete(*self.tree.get_children())
        self.output_box.delete("1.0", "end")
        self.detail_box.delete("1.0", "end")
        self.parsed_data = None
        self.node_data = {}

    def expand_all(self):
        def _expand(item):
            self.tree.item(item, open=True)
            for c in self.tree.get_children(item):
                _expand(c)
        for item in self.tree.get_children():
            _expand(item)

    def collapse_all(self):
        def _collapse(item):
            self.tree.item(item, open=False)
            for c in self.tree.get_children(item):
                _collapse(c)
        for item in self.tree.get_children():
            _collapse(item)

    def get_formatted_text(self):
        return self.output_box.get("1.0", "end-1c").strip()

    def apply_language(self, lang):
        self.lang = lang
        self.lbl_input.config(text=t("input_label", lang))
        self.lbl_tree.config(text=t("tree_label", lang))
        self.tree.heading("#0", text=t("tree_col_key", lang))
        self.tree.heading("value", text=t("tree_col_val", lang))
        self.detail_frame.config(text=t("detail_label", lang))
        self.lbl_output.config(text=t("output_label", lang))
        if self.parsed_data is not None:
            self.tree.delete(*self.tree.get_children())
            self.node_data = {}
            if isinstance(self.parsed_data, dict):
                root_node = self.tree.insert("", "end", text="(root)",
                                              values=(t("obj_summary", lang, len=len(self.parsed_data)),))
                self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
                for key, val in self.parsed_data.items():
                    build_tree(self.tree, root_node, key, val, self.node_data, lang)
                self.tree.item(root_node, open=True)
            elif isinstance(self.parsed_data, list):
                root_node = self.tree.insert("", "end", text="(root)",
                                              values=(t("list_summary", lang, len=len(self.parsed_data)),))
                self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
                for i, item in enumerate(self.parsed_data):
                    build_tree(self.tree, root_node, f"[{i}]", item, self.node_data, lang)
                self.tree.item(root_node, open=True)


# ============================================================
# GUI 主界面（标签页管理）
# ============================================================

class JsonTreeViewer:
    def __init__(self, root):
        self.root = root
        self.lang = "zh"
        self.tabs = []
        self.tab_counter = 0
        root.title(t("title", self.lang))
        root.geometry("1100x750")
        root.minsize(800, 500)

        style = ttk.Style()
        style.theme_use("clam")

        # ====== 工具栏 ======
        toolbar = ttk.Frame(root, padding=(8, 6))
        toolbar.pack(fill="x")

        self.lbl_toolbar = ttk.Label(toolbar, text=t("toolbar_label", self.lang))
        self.lbl_toolbar.pack(side="left")
        self.btn_parse = ttk.Button(toolbar, text=t("btn_parse", self.lang), command=self.parse_active)
        self.btn_parse.pack(side="left", padx=(4, 12))
        self.btn_clear = ttk.Button(toolbar, text=t("btn_clear", self.lang), command=self.clear_active)
        self.btn_clear.pack(side="left")
        self.btn_expand = ttk.Button(toolbar, text=t("btn_expand", self.lang), command=self.expand_active)
        self.btn_expand.pack(side="left", padx=(4, 0))
        self.btn_collapse = ttk.Button(toolbar, text=t("btn_collapse", self.lang), command=self.collapse_active)
        self.btn_collapse.pack(side="left", padx=(4, 0))
        self.btn_copy = ttk.Button(toolbar, text=t("btn_copy", self.lang), command=self.copy_active)
        self.btn_copy.pack(side="left", padx=(12, 0))
        self.btn_paste = ttk.Button(toolbar, text=t("btn_paste", self.lang), command=self.paste_active)
        self.btn_paste.pack(side="left", padx=(4, 0))
        self.btn_lang = ttk.Button(toolbar, text=t("btn_lang", self.lang), command=self.toggle_language)
        self.btn_lang.pack(side="right", padx=(4, 0))

        # ====== 标签栏（仅按钮） ======
        tab_bar = ttk.Frame(root)
        tab_bar.pack(fill="x", padx=8, pady=(2, 0))
        ttk.Label(tab_bar, text="标签页:").pack(side="left")
        self.btn_new_tab = ttk.Button(tab_bar, text="+", width=3, command=self.add_tab)
        self.btn_new_tab.pack(side="left", padx=(4, 2))
        self.btn_del_tab = ttk.Button(tab_bar, text="×", width=3, command=self.close_active_tab)
        self.btn_del_tab.pack(side="left")

        # ====== 标签内容区 ======
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ====== 状态栏 ======
        self.status = ttk.Label(root, text=t("status_ready", self.lang), relief="sunken", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0, 4))

        self.add_tab()

    # ====== 标签管理 ======

    def active_tab(self):
        idx = self.notebook.index("current")
        return self.tabs[idx] if self.tabs else None

    def add_tab(self):
        self.tab_counter += 1
        name = f"Tab {self.tab_counter}"
        frame = ttk.Frame(self.notebook)
        tab = JsonTab(frame, self.lang, self)
        self.tabs.append(tab)
        self.notebook.add(frame, text=name)
        self.notebook.select(frame)

    def close_active_tab(self):
        """× 按钮：关闭当前标签"""
        if len(self.tabs) <= 1:
            return
        idx = self.notebook.index("current")
        self.tabs.pop(idx)
        self.notebook.forget(idx)

    # ====== 工具栏操作 → 转发到激活标签 ======

    def parse_active(self):
        tab = self.active_tab()
        if tab:
            ok, msg = tab.parse()
            self.status.config(text=msg)

    def clear_active(self):
        tab = self.active_tab()
        if tab:
            tab.clear()
            self.status.config(text=t("status_cleared", self.lang))

    def expand_active(self):
        tab = self.active_tab()
        if tab:
            tab.expand_all()

    def collapse_active(self):
        tab = self.active_tab()
        if tab:
            tab.collapse_all()

    def copy_active(self):
        tab = self.active_tab()
        if tab:
            text = tab.get_formatted_text()
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.status.config(text=t("status_copied", self.lang))
            else:
                self.status.config(text=t("status_nocopy", self.lang))

    def paste_active(self):
        tab = self.active_tab()
        if not tab:
            return
        try:
            text = self.root.clipboard_get()
            tab.input_box.delete("1.0", "end")
            tab.input_box.insert("1.0", text)
            self.status.config(text=t("status_pasted", self.lang))
        except Exception:
            self.status.config(text=t("status_clip_fail", self.lang))

    # ====== 语言切换 ======

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        lg = self.lang
        self.root.title(t("title", lg))
        self.lbl_toolbar.config(text=t("toolbar_label", lg))
        self.btn_parse.config(text=t("btn_parse", lg))
        self.btn_clear.config(text=t("btn_clear", lg))
        self.btn_expand.config(text=t("btn_expand", lg))
        self.btn_collapse.config(text=t("btn_collapse", lg))
        self.btn_copy.config(text=t("btn_copy", lg))
        self.btn_paste.config(text=t("btn_paste", lg))
        self.btn_lang.config(text=t("btn_lang", lg))
        self.status.config(text=t("status_ready", lg))
        for tab in self.tabs:
            tab.apply_language(lg)


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonTreeViewer(root)
    root.mainloop()
