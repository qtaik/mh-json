"""
JSON 层级可视化工具 — APP 渗透专用 GUI 版
用法: python json_tree_viewer.py
功能:
  - 粘贴 Burp 抓到的请求体 → 自动解析嵌套 JSON + JWT
  - 左侧: 树状图（可折叠/展开，一眼看清层级）
  - 右侧: 完整美化 JSON 输出
  - 零依赖，Python 自带 tkinter
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

def build_tree(tree_widget, parent_id, key, val, max_depth=10, _depth=0):
    """
    递归构建 ttk.Treeview 节点
    自动展开 JSON 字符串、JWT、嵌套 dict/list
    """
    if _depth >= max_depth:
        return

    label = str(key) if key is not None else "(root)"

    if isinstance(val, dict):
        node = tree_widget.insert(parent_id, "end", text=label,
                                   values=(f"{{对象, {len(val)} 个键}}",))
        for k, v in val.items():
            build_tree(tree_widget, node, k, v, max_depth, _depth + 1)

    elif isinstance(val, list):
        node = tree_widget.insert(parent_id, "end", text=label,
                                   values=(f"[列表, {len(val)} 项]",))
        for i, item in enumerate(val):
            build_tree(tree_widget, node, f"[{i}]", item, max_depth, _depth + 1)

    elif is_json_string(val):
        try:
            decoded = json.loads(val)
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=("[JSON 字符串 → 已展开]",))
            for k, v in decoded.items() if isinstance(decoded, dict) else enumerate(decoded):
                key_label = k if isinstance(decoded, dict) else f"[{k}]"
                build_tree(tree_widget, node, key_label, v, max_depth, _depth + 1)
        except Exception:
            tree_widget.insert(parent_id, "end", text=label,
                               values=("[JSON 解析失败]",))

    elif is_jwt(val):
        decoded = decode_jwt_payload(val)
        if decoded:
            node = tree_widget.insert(parent_id, "end", text=label,
                                       values=("[JWT → 已解码]",))
            for k, v in decoded.items():
                build_tree(tree_widget, node, k, v, max_depth, _depth + 1)
        else:
            tree_widget.insert(parent_id, "end", text=label,
                               values=(f"[JWT, {len(val)} 字符]",))

    elif isinstance(val, str):
        s = val.replace("\n", "\\n").replace("\t", "\\t")
        tree_widget.insert(parent_id, "end", text=label,
                           values=(s,))

    elif val is None:
        tree_widget.insert(parent_id, "end", text=label, values=("null",))

    else:
        tree_widget.insert(parent_id, "end", text=label, values=(str(val),))


# ============================================================
# GUI 主界面
# ============================================================

class JsonTreeViewer:
    def __init__(self, root):
        self.root = root
        root.title("JSON 层级可视化 — APP 渗透专用")
        root.geometry("1100x750")
        root.minsize(800, 500)

        # 全局样式
        style = ttk.Style()
        style.theme_use("clam")

        # ====== 顶部工具栏 ======
        toolbar = ttk.Frame(root, padding=(8, 6))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="粘贴 Burp 请求体 JSON → ").pack(side="left")
        ttk.Button(toolbar, text="解析", command=self.parse_input).pack(side="left", padx=(4, 12))
        ttk.Button(toolbar, text="清空", command=self.clear_all).pack(side="left")
        ttk.Button(toolbar, text="展开全部", command=self.expand_all).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="折叠全部", command=self.collapse_all).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="复制美化 JSON", command=self.copy_formatted).pack(side="left", padx=(12, 0))
        ttk.Button(toolbar, text="从剪贴板粘贴", command=self.paste_clipboard).pack(side="left", padx=(4, 0))

        # ====== 主区域: 左右分栏 ======
        main_pane = ttk.PanedWindow(root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ---- 左栏: 输入 + 树状图 ----
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        ttk.Label(left_frame, text="输入（粘贴 JSON）:", anchor="w").pack(fill="x", padx=4, pady=(4, 0))
        self.input_box = scrolledtext.ScrolledText(
            left_frame, height=8, wrap="none",
            font=("Consolas", 10)
        )
        self.input_box.pack(fill="both", expand=False, padx=4, pady=(2, 8))

        ttk.Label(left_frame, text="树状图（可展开/折叠）:", anchor="w").pack(fill="x", padx=4, pady=(0, 0))

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=(2, 2))

        # Treeview: 两列 — 节点名 | 值
        self.tree = ttk.Treeview(tree_frame, columns=("value",), show="tree headings",
                                  selectmode="browse")
        self.tree.heading("#0", text="节点")
        self.tree.heading("value", text="值 → 点开节点查看详情")
        self.tree.column("#0", width=260, stretch=True)
        self.tree.column("value", width=320, stretch=True)

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # ---- 右栏: 美化 JSON 输出 ----
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)

        ttk.Label(right_frame, text="美化 JSON（完整输出）:", anchor="w").pack(fill="x", padx=4, pady=(4, 0))
        self.output_box = scrolledtext.ScrolledText(
            right_frame, wrap="none",
            font=("Consolas", 10), bg="#f5f5f5"
        )
        self.output_box.pack(fill="both", expand=True, padx=4, pady=(2, 2))

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

        # 构建树
        if isinstance(self.parsed_data, dict):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(f"{{对象, {len(self.parsed_data)} 个键}}",))
            for key, val in self.parsed_data.items():
                build_tree(self.tree, root_node, key, val)
            # 自动展开 root
            self.tree.item(root_node, open=True)
        elif isinstance(self.parsed_data, list):
            root_node = self.tree.insert("", "end", text="(root)",
                                          values=(f"[数组, {len(self.parsed_data)} 项]",))
            for i, item in enumerate(self.parsed_data):
                build_tree(self.tree, root_node, f"[{i}]", item)
            self.tree.item(root_node, open=True)

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
