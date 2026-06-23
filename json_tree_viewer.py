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


def value_summary(val):
    """生成值的简短摘要（显示在树节点上）"""
    if isinstance(val, str) and is_json_string(val):
        return f"[JSON 字符串, {len(val)} 字符]"
    elif isinstance(val, str) and is_jwt(val):
        return f"[JWT, {len(val)} 字符]"
    elif isinstance(val, str):
        s = val.replace("\n", " ").replace("\t", " ")
        if len(s) <= 60:
            return repr(val)
        else:
            return repr(s[:57] + "...")
    elif isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        return f"[列表, {len(val)} 项]"
    elif isinstance(val, dict):
        return f"{{对象, {len(val)} 个键}}"
    elif val is None:
        return "null"
    return str(val)


# ============================================================
# 构建树 + 递归解析
# ============================================================

def build_tree(tree_widget, parent_id, key, val, data_store, max_depth=10, _depth=0):
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
                                   values=(f"{{对象, {len(val)} 个键}}",))
        data_store[node] = json.dumps(val, indent=2, ensure_ascii=False)
        for k, v in val.items():
            build_tree(tree_widget, node, k, v, data_store, max_depth, _depth + 1)

    elif isinstance(val, list):
        node = tree_widget.insert(parent_id, "end", text=label,
                                   values=(f"[列表, {len(val)} 项]",))
        data_store[node] = json.dumps(val, indent=2, ensure_ascii=False)
        for i, item in enumerate(val):
            build_tree(tree_widget, node, f"[{i}]", item, data_store, max_depth, _depth + 1)

    elif is_json_string(val):
        try:
            decoded = json.loads(val)
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=("[JSON 字符串 → 已展开]",))
            data_store[node] = json.dumps(decoded, indent=2, ensure_ascii=False)
            items = decoded.items() if isinstance(decoded, dict) else enumerate(decoded)
            for k, v in items:
                key_label = k if isinstance(decoded, dict) else f"[{k}]"
                build_tree(tree_widget, node, key_label, v, data_store, max_depth, _depth + 1)
        except Exception:
            node = tree_widget.insert(parent_id, "end", text=label,
                               values=("[JSON 解析失败]",))
            data_store[node] = val

    elif is_jwt(val):
        decoded = decode_jwt_payload(val)
        if decoded:
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=("[JWT → 已解码]",))
            data_store[node] = json.dumps(decoded, indent=2, ensure_ascii=False)
            for k, v in decoded.items():
                build_tree(tree_widget, node, k, v, data_store, max_depth, _depth + 1)
        else:
            node = tree_widget.insert(parent_id, "end", text=label,
                               values=(f"[JWT, {len(val)} 字符]",))
            data_store[node] = val

    elif isinstance(val, str):
        s = val.replace("\n", "\\n").replace("\t", "\\t")
        node = tree_widget.insert(parent_id, "end", text=label,
                           values=(s,))
        data_store[node] = val

    elif val is None:
        node = tree_widget.insert(parent_id, "end", text=label, values=("null",))
        data_store[node] = "null"

    else:
        node = tree_widget.insert(parent_id, "end", text=label, values=(str(val),))
        data_store[node] = str(val)


# ============================================================
# GUI 主界面
# ============================================================

class JsonTreeViewer:
    def __init__(self, root):
        self.root = root
        root.title("JSON 层级可视化")
        root.geometry("1100x750")
        root.minsize(800, 500)

        # 全局样式
        style = ttk.Style()
        style.theme_use("clam")

        # ====== 顶部工具栏 ======
        toolbar = ttk.Frame(root, padding=(8, 6))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="粘贴 JSON → ").pack(side="left")
        ttk.Button(toolbar, text="解析", command=self.parse_input).pack(side="left", padx=(4, 12))
        ttk.Button(toolbar, text="清空", command=self.clear_all).pack(side="left")
        ttk.Button(toolbar, text="展开全部", command=self.expand_all).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="折叠全部", command=self.collapse_all).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="复制美化 JSON", command=self.copy_formatted).pack(side="left", padx=(12, 0))
        ttk.Button(toolbar, text="从剪贴板粘贴", command=self.paste_clipboard).pack(side="left", padx=(4, 0))

        # ====== 主区域: 左右分栏（可拖拽） ======
        main_pane = ttk.PanedWindow(root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ========== 左栏: 输入 + 树状图 + 详情（纵向可拖拽） ==========
        left_pane = ttk.PanedWindow(main_pane, orient="vertical")
        main_pane.add(left_pane, weight=1)

        # -- 输入框 --
        input_frame = ttk.Frame(left_pane)
        ttk.Label(input_frame, text="输入（粘贴 JSON）:", anchor="w").pack(fill="x", padx=4, pady=(4, 0))

        # 手写带横纵滚动条的文本框
        input_inner = ttk.Frame(input_frame)
        input_inner.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        self.input_box = tk.Text(input_inner, wrap="none", font=("Consolas", 10),
                                  height=6, undo=True)
        input_scroll_y = ttk.Scrollbar(input_inner, orient="vertical", command=self.input_box.yview)
        input_scroll_x = ttk.Scrollbar(input_inner, orient="horizontal", command=self.input_box.xview)
        self.input_box.configure(yscrollcommand=input_scroll_y.set, xscrollcommand=input_scroll_x.set)
        self.input_box.grid(row=0, column=0, sticky="nsew")
        input_scroll_y.grid(row=0, column=1, sticky="ns")
        input_scroll_x.grid(row=1, column=0, sticky="ew")
        input_inner.rowconfigure(0, weight=1)
        input_inner.columnconfigure(0, weight=1)

        left_pane.add(input_frame, weight=1)

        # -- 树状图 --
        tree_frame = ttk.Frame(left_pane)

        ttk.Label(tree_frame, text="树状图（可展开/折叠）:", anchor="w").pack(fill="x", padx=4, pady=(0, 0))

        tree_inner = ttk.Frame(tree_frame)
        tree_inner.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        self.tree = ttk.Treeview(tree_inner, columns=("value",), show="tree headings",
                                  selectmode="browse")
        self.tree.heading("#0", text="节点")
        self.tree.heading("value", text="值 → 点击查看完整值")
        self.tree.column("#0", width=260, stretch=True)
        self.tree.column("value", width=320, stretch=True)

        tree_scroll_y = ttk.Scrollbar(tree_inner, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_inner, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        tree_inner.rowconfigure(0, weight=1)
        tree_inner.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_node_select)

        left_pane.add(tree_frame, weight=3)

        # -- 详情面板 --
        detail_frame = ttk.LabelFrame(left_pane, text="选中节点完整值（点击树节点查看）", padding=(4, 2))
        self.detail_box = scrolledtext.ScrolledText(
            detail_frame, height=4, wrap="word",
            font=("Consolas", 10), bg="#fffff0"
        )
        self.detail_box.pack(fill="both", expand=True)
        left_pane.add(detail_frame, weight=1)

        # ========== 右栏: 美化 JSON 输出 ==========
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)

        ttk.Label(right_frame, text="美化 JSON（完整输出）:", anchor="w").pack(fill="x", padx=4, pady=(4, 0))

        output_inner = ttk.Frame(right_frame)
        output_inner.pack(fill="both", expand=True, padx=4, pady=(2, 2))
        self.output_box = tk.Text(output_inner, wrap="none", font=("Consolas", 10),
                                   bg="#f5f5f5", undo=True)
        output_scroll_y = ttk.Scrollbar(output_inner, orient="vertical", command=self.output_box.yview)
        output_scroll_x = ttk.Scrollbar(output_inner, orient="horizontal", command=self.output_box.xview)
        self.output_box.configure(yscrollcommand=output_scroll_y.set, xscrollcommand=output_scroll_x.set)
        self.output_box.grid(row=0, column=0, sticky="nsew")
        output_scroll_y.grid(row=0, column=1, sticky="ns")
        output_scroll_x.grid(row=1, column=0, sticky="ew")
        output_inner.rowconfigure(0, weight=1)
        output_inner.columnconfigure(0, weight=1)

        # ====== 状态栏 ======
        self.status = ttk.Label(root, text="就绪 — 粘贴 JSON 后点「解析」", relief="sunken", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0, 4))

        self.parsed_data = None

    # ====== 操作 ======

    def parse_input(self):
        """解析输入框中的 JSON"""
        raw = self.input_box.get("1.0", "end-1c").strip()
        if not raw:
            self.status.config(text="❌ 输入为空")
            return

        try:
            self.parsed_data = json.loads(raw)
        except json.JSONDecodeError as e:
            self.status.config(text=f"❌ JSON 解析失败: {e}")
            return

        # 清空旧的
        self.tree.delete(*self.tree.get_children())
        self.output_box.delete("1.0", "end")
        self.detail_box.delete("1.0", "end")
        self.node_data = {}  # node_id → 完整值

        # 构建树
        if isinstance(self.parsed_data, dict):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(f"{{对象, {len(self.parsed_data)} 个键}}",))
            self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
            for key, val in self.parsed_data.items():
                build_tree(self.tree, root_node, key, val, self.node_data)
            self.tree.item(root_node, open=True)
        elif isinstance(self.parsed_data, list):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(f"[数组, {len(self.parsed_data)} 项]",))
            self.node_data[root_node] = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
            for i, item in enumerate(self.parsed_data):
                build_tree(self.tree, root_node, f"[{i}]", item, self.node_data)
            self.tree.item(root_node, open=True)

        self.status.config(text=f"✅ 解析成功 — 点击左侧节点查看完整值")

        # 输出美化 JSON
        formatted = json.dumps(self.parsed_data, indent=2, ensure_ascii=False)
        self.output_box.insert("1.0", formatted)

        # 统计
        self.status.config(
            text=f"✅ 解析成功 — 根层: {len(self.parsed_data) if isinstance(self.parsed_data, dict) else 'array'} 个键"
        )

    def clear_all(self):
        """清空所有内容"""
        self.input_box.delete("1.0", "end")
        self.tree.delete(*self.tree.get_children())
        self.output_box.delete("1.0", "end")
        self.parsed_data = None
        self.status.config(text="已清空")

    def expand_all(self):
        for item in self.tree.get_children():
            self._expand_recursive(item)

    def _expand_recursive(self, item):
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self._expand_recursive(child)

    def collapse_all(self):
        for item in self.tree.get_children():
            self._collapse_recursive(item)

    def _collapse_recursive(self, item):
        self.tree.item(item, open=False)
        for child in self.tree.get_children(item):
            self._collapse_recursive(child)

    def copy_formatted(self):
        text = self.output_box.get("1.0", "end-1c").strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status.config(text="✅ 已复制美化 JSON 到剪贴板")
        else:
            self.status.config(text="⚠️ 没有内容可复制")

    def on_node_select(self, event):
        """点击树节点 → 在详情面板显示完整值"""
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        full_value = self.node_data.get(item, "")
        self.detail_box.delete("1.0", "end")
        if full_value:
            node_text = self.tree.item(item, "text")
            self.detail_box.insert("1.0", f"# {node_text}\n\n{full_value}")

    def paste_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)
            self.status.config(text="已粘贴剪贴板内容，点「解析」查看")
        except Exception:
            self.status.config(text="❌ 剪贴板为空或不可读")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonTreeViewer(root)
    root.mainloop()
