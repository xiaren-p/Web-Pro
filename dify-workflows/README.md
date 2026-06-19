# Dify 工作流配置

> 本目录存放 ERP AI 助手用到的 Dify 应用编排导出文件（DSL）。
> **DSL 文件是档案，不是部署源**——Dify 不支持"覆盖现有应用"，DSL 只用于第一次创建应用或灾难恢复重建。
> 平时改动直接在 Dify 编排页操作，改完再导出 DSL 覆盖本地文件保持同步。

## 文件清单

| 文件 | 用途 |
| ---- | ---- |
| [erp-ai-assistant.yml](erp-ai-assistant.yml) | ERP AI 助手主对话流，含思考模式双模型分流（R1 推理 / V3 快答） |

## 工作流架构

```text
开始节点 (thinking_mode 变量)
   │
   ↓
IF/ELSE 条件分支
   │
   ├─ thinking_mode == 'on'  → LLM-推理（DeepSeek-R1）→ 直接回复
   │                           （自动输出 <think>...</think> 推理过程）
   │
   └─ 否则                    → LLM-快答（DeepSeek-V3 / Chat）→ 直接回复
                               （直接给答案，禁止输出 think 标签）
```

## 前后端契约

```text
前端「思考」chip 状态
   ├─ 开 → inputs.thinking_mode = "on"
   └─ 关 → inputs.thinking_mode = "off"
        ↓
   Dify 开始节点接收变量
        ↓
   IF/ELSE 节点根据值分流到对应 LLM
        ↓
   两个 LLM 都汇入「直接回复」节点
        ↓
   前端 MessageItem.vue 解析 <think> 标签 → 折叠展示
```

## 开始节点变量

| 字段 | 值 |
| ---- | ---- |
| 变量名 | `thinking_mode` |
| 类型 | `select` |
| 必填 | 否 |
| 默认 | `off` |
| 选项 | `on` / `off` |

## 模型选择

| 节点 | 模型 | 用途 |
| ---- | ---- | ---- |
| LLM-推理 | `deepseek-reasoner`（DeepSeek-R1） | 真深度思考，自带 `<think>` 标签 |
| LLM-快答 | `deepseek-chat`（DeepSeek-V3） | 普通对话，秒级响应 |

如需用其他推理模型替换 R1：

| 模型 | provider 字段 | name 字段 |
| ---- | ---- | ---- |
| Qwen3-Thinking-235B | `langgenius/dashscope/dashscope` | `qwen3-235b-a22b` |
| OpenAI o3-mini | `langgenius/openai/openai` | `o3-mini` |
| Claude Sonnet 4 (extended thinking) | `langgenius/anthropic/anthropic` | `claude-sonnet-4-20250514` |

## 首次部署到 Dify

1. Dify 后台 → **工作室** → **创建应用**
2. 选择 **Chatflow** 类型 → 顶部 Tab 切换到 **「导入 DSL」** → 上传 `erp-ai-assistant.yml`
3. 创建后进入应用 → 左侧菜单 **「访问 API」** → 创建 API 密钥
4. 把密钥填到服务器 `.env`：

   ```bash
   DIFY_API_BASE=http://你的Dify地址
   DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxxx
   ```

5. 重启 Celery worker：

   ```bash
   sudo systemctl restart celery-default celery-parallel celery-single
   ```

## ⚠️ Dify 不支持"覆盖现有应用"

**Dify 大部分版本只能"导入 DSL 创建新应用"，不能用 DSL 覆盖已有应用配置**。

所以日常工作流应该是：

1. **平时改动**：直接在 Dify 编排页修改 → 右上角【发布更新】
2. **改完同步本地**：编排页 → 右上角【⋯】→「导出 DSL」→ 覆盖本目录的 yml
3. **本地 yml 是档案**，不是部署源；只在第一次部署或重建应用时使用

## 测试方法

进入 Dify 应用编排页右侧的预览窗口：

```text
1. 思考模式开关：选「关闭」 → 输入"你好" → 应该秒回，无 <think>
2. 思考模式开关：选「开启」 → 输入"分析房价上涨原因" → 应看到推理过程 + 答案
```

## 接 Plan Mode（结构化方案卡片）

让 AI 输出 Plan 卡片让用户勾选确认（参考 `CLAUDE.md` 第三章 Plan Schema）。
推荐做法：在两个 LLM 节点的提示词末尾各加一段：

```text
当你判断需要让用户做选择 / 确认时（如"创建采购单"、"调整广告预算"），
除了自然语言说明，必须额外输出一段 <plan>...</plan> 包裹的 JSON：

<plan>
{
  "title": "卡片标题",
  "description": "简短说明",
  "options": [
    {"key": "stable_id_1", "label": "用户看到的文案"}
  ],
  "multi_select": false,
  "allow_custom": true,
  "custom_field": {"key": "remark", "label": "备注", "placeholder": "选填"},
  "confirm_action": {"endpoint": "", "method": "POST", "button_text": "确认"},
  "cancellable": true
}
</plan>

约束：
- options 的 key 必须是英文 / 数字组合
- 一次回复最多输出 1 个 <plan>
- 不需要选择时不要输出 plan 标签
```

后端 `plan_translator.py` 会自动从 `<plan>...</plan>` 提取并归一化为前端 Schema。

## 模型成本参考（仅供决策）

| 模型 | 单价（输入/输出） | 速度 | 适用场景 |
| ---- | ---- | ---- | ---- |
| `deepseek-chat` (V3) | ¥1 / ¥2 每百万 token | 秒级 | 普通对话、快答 |
| `deepseek-reasoner` (R1) | ¥4 / ¥16 每百万 token | 10~60 秒 | 深度推理、复杂问题 |

R1 输入价是 V3 的 4 倍、输出价是 8 倍，但只有用户主动开启「思考」chip 才会触发，整体成本可控。
