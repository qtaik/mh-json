# MH-JSON — 嵌套 JSON 层级可视化工具

专为 APP 渗透测试设计的 JSON 数据包分析工具。把 Burp Suite 抓到的复杂嵌套 JSON 请求体丢进去，自动拆解层级结构、解码 JWT、生成树状图和美化输出。

## 痛点

APP 渗透抓包（尤其是 uni-app / Serverless 架构）经常遇到这种 JSON：

```json
{"method":"...","params":"{\"functionTarget\":\"...\",\"functionArgs\":\"{\\\"command\\\":...}\"}"}
```

三层 JSON 套娃 + JWT token，手动读根本看不清结构。这个工具一键解开。

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

1. 在 Burp Suite 中抓到请求 → 右键 body → Copy
2. 打开工具 → 粘贴 → 点「解析」
3. 左侧树状图任意展开/折叠，右侧看美化后的完整 JSON
4. 点「复制美化 JSON」贴回 Burp 或笔记

## 截图


## 依赖

**零依赖** — Python 3 自带 tkinter，无需 pip install 任何东西。

## 适用场景

- APP 渗透测试抓包分析
- uni-app / uniCloud / Serverless 架构的请求体拆解
- JWT Token 快速解码
- 复杂嵌套 API 调试
- 后端接口逆向

## License

MIT
