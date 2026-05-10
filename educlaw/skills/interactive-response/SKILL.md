---
name: interactive-response
description: 交互式响应 — 当需要用户从多个选项中选择或补充信息时，使用 <action> 标签生成可点击的交互组件。让对话不再是纯文本，用户可以点击按钮或填写输入框来继续对话。
---

# 交互式响应

## 核心规则（必须遵守）

**1. <action> 即内容：** `<action>` 标签本身就是回复的核心内容，不要在外面再用文字表格重复一遍同样的数据。前端会把标签渲染成可点击组件，用户看不到原始标签。

**2. 简洁前置：** 在 `<action>` 前面只写一两句引导语，不要大段描述。

**3. 禁止重复：** 已经写在 `<action>` 里的选项，不要再以纯文本形式罗列一遍。

正确示例：
```
你好，Demo！我是 EduClaw。想从哪里开始？

<action type="select" id="main_menu">
| 功能 | 说明 |
|------|------|
| warning | 学业预警 |
| profile | 能力画像 |
| search | 课程检索 |
</action>
```

错误示例（禁止）：
```
你好，Demo！以下是功能列表：
1. warning - 学业预警
2. profile - 能力画像
3. search - 课程检索

<action type="select" id="main_menu">
| 功能 | 说明 |
|------|------|
| warning | 学业预警 |
| profile | 能力画像 |
</action>
```
上方重复罗列了与 action 相同的内容，禁止这样做。

## select 格式

```xml
<action type="select" id="唯一ID">
| 值 | 显示名 | 补充信息 |
|----|--------|----------|
</action>
```

## input 格式

```xml
<action type="input" id="唯一ID" prompt="输入提示">
</action>
```
