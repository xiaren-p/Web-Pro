# 数据采集

「数据采集」模块管理爬虫的类目、采集节点配置、卖家精灵账号与爬虫日志。多数接口为开放接口，供外部采集节点回写数据。

## 入口

侧边栏包含数据采集相关页面：

- 爬取类目（路由 `/crawler/category`）
- 采集配置（路由 `/crawler/conf`）
- 爬虫日志（路由 `/crawler/logs`）

## 爬取类目

### 表格列

类目名称、站点、节点 ID、状态、创建时间等。

### 操作

- **新增 / 编辑**：`CategoryFormDialog` 填写类目名称、站点、节点 ID 等。
- **查看**：`CategoryViewDialog` 查看类目详情。
- 后端端点 `/api/v1/crawler/category`（`CrawlerCategory` 模型 CRUD）。

## 采集配置

### 服务节点配置

`ServerConfig` / `ServerFormDialog` 管理采集服务节点：

- 字段：节点地址、Token、状态。
- 后端端点 `/api/v1/crawler/conf`（`CrawlerConf` 模型 CRUD）。

### 卖家精灵账号配置

`SellerConfig` / `SellerFormDialog` 管理卖家精灵账号凭据：

- 字段：账号、密码 / Token、状态。
- 后端端点 `/api/v1/crawler/seller`（`CrawlerSellerAccount` 模型 CRUD）。

## 爬虫日志

### 表格列

任务名、状态、抓取条数、耗时、错误信息、时间。

### 搜索

按状态、时间筛选。

### 后端端点

`/api/v1/crawler/logs`（`CrawlerLog` 模型）。

## 开放接口说明

采集相关接口多数为开放接口（无需登录鉴权），供部署在外部的采集节点回写数据。具体开放范围以后端 `crawler/` 视图配置为准。
