# 开发规范要点

本文摘录项目最易被违反的开发规范。完整规范见 `CLAUDE.md`（随仓库分发的权威总纲）与 `AGENTS.md`（执行备忘）。

## 命名与注释

- **英文命名 + 中文注释**：类/变量/函数/数据库字段全英文，禁拼音、禁中英混搭；类与函数强制完整中文 Docstring，讲清「为什么（Why）」。
- 技术债标记：`# TODO(优化/张三): 待XX优化` / `// FIXME(Bug/李四): ...`。
- 文件命名：Python `snake_case.py`、前端组件 `PascalCase.vue`、文档 `kebab-case.md`。

## 后端

- **绝对路径导入**：`from api_v1...` / `from api_v2...`，禁相对导入。
- **Google Style 中文 Docstring**：含 `Args` / `Returns` / `Raises` / `Examples`。
- **强制 Type Hints**：入参/返回值/类属性必须标注，禁 `Any` 铺满。
- **卫语句 + 嵌套 ≤ 3**；方法 > 50 行抽 `_xxx`；禁 `# ======` 长分隔注释，改 `# 主题：说明`。
- **一类一文件**：每个 Model / Serializer / View / Service / Celery Task 一个 `.py`。
- **日志**：禁 `print()`，走 Logger，每条带 `[类名] [方法名]` 前缀，`ERROR` 带 `exc_info=True`，禁裸 `except: pass`。
- **网络鲁棒性**：`requests` 必须写 `timeout`；`with open` 释放句柄；批量遍历切片。

## 前端

- **绝对路径导入**：`@/...`，禁相对路径。
- **强制 `<script setup lang="ts">`**：禁 Options API，禁裸 `<script>`。
- **JSDoc 中文注释**：类/对外函数 `/** ... */` + `@param` / `@returns` / `@throws`。
- **消灭 `any`**：走 `unknown` + 类型守卫；禁 `@ts-ignore` / `eslint-disable`（特殊情况跟中文 TODO）。
- **样式隔离**：`<style scoped lang="scss">`，穿透用 `:deep()` 且在父级选择器内。
- **三段式顺序**：`<template>` → `<script setup lang="ts">` → `<style scoped lang="scss">`。
- **单 SFC ≤ 400 行**；`defineProps` 带 TS 泛型，`defineEmits` 显式签名。
- **网络请求经 `src/api/` 封装**，禁视图/组件直接 `axios` / `fetch`。
- **网络熔断**：触发后端通信的按钮先 `loading.value = true`。

## 架构铁律

- **职责归类**：字段映射/校验 → `serializers/`；表结构 → `models/`；业务计算 → `services/`；HTTP 解析 → `views/`。禁 view 拼字典、禁 model 写跨表计算。
- **数据出口最终成形**：枚举翻译、金额/日期/单位格式化、字段重命名、聚合统计必须在**后端**完成；前端拿到即可渲染，禁在前端做业务字段重映射或格式化。
- **分层 + 非阻塞**：UI/Controller 与 Service 物理分离；耗时 IO/计算入异步任务。

## 提交前检查

- 前端至少跑 `pnpm run type-check` 与 `pnpm run lint:eslint`。
- 确保无未使用变量、未处理警告、违反 `eslint.config.ts` 的语法问题。
- 禁 `// eslint-disable-next-line` / `@ts-ignore` 掩盖错误。
- 禁将 `test_xxx` / `temp_run.py` 等临时文件推进主库。
- 变更 Model 时 commit 只含 Model 文件，不含迁移文件（CLAUDE.md §1.8）。
