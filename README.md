# MH-JSON — 嵌套 JSON 层级可视化工具

把嵌套复杂、层层套娃的 JSON 丢进去，自动拆解层级结构、解码 JWT、生成树状图和美化输出。

## 痛点

调试时经常遇到三层 JSON 套娃 + JWT token 的请求体：

```json
{"method":"...","params":"{\"functionTarget\":\"...\",\"functionArgs\":\"{\\\"command\\\":...}\"}"}
```

手动读根本看不清结构。这个工具一键解开。

## 功能

- ✅ 嵌套 JSON 自动逐层展开（无论套几层）
- ✅ JWT Token 自动解码并展开 Payload
- ✅ 左侧可折叠树状图（一眼看清层级关系）
- ✅ 右侧美化 JSON 完整输出
- ✅ 一键复制美化结果
- ✅ 零依赖，Python 3 自带 tkinter

## 快速开始

```bash
python json_tree_viewer.py
```

1. 复制你的 JSON 数据
2. 打开工具 → 粘贴 → 点「解析」
3. 左侧树状图任意展开/折叠，右侧看美化后的完整 JSON
4. 点「复制美化 JSON」即可使用

## 截图


## 依赖

**零依赖** — Python 3 自带 tkinter，无需 pip install 任何东西。

## 适用场景

- 复杂嵌套 JSON 结构分析
- JWT Token 快速解码
- API 请求/响应体拆解
- 后端接口调试
- 学习 JSON 数据结构

## License

MIT
