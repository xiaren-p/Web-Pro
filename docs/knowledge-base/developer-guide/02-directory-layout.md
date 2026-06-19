# 目录结构

本文详列前后端目录布局，便于定位代码。

## 后端 `backend-master/`

```text
backend-master/
├── backend_master/          项目配置（settings / urls / celery / asgi / wsgi / 路由器）
│   ├── settings.py          Django 配置（含 Celery 路由表与 Beat 调度）
│   ├── urls.py              根 URL 入口
│   ├── celery.py            Celery 应用
│   ├── analytics_database_router.py   Doris 分析库路由器
│   └── doris_backend/       Doris 自定义数据库后端
├── api_v1/                  业务接口 App（CRUD）
│   ├── auth/                认证后端（BearerTokenAuthentication）
│   ├── middleware/          HTTP 中间件
│   ├── permissions/         DRF 权限类（menu_perm_required）
│   ├── models/              数据模型（按板块子目录）
│   │   ├── crawler/  file/  finance/  lingxing/  nc/  notice/  system/
│   ├── serializers/         序列化器（按板块子目录）
│   ├── services/            业务服务（lingxing/、nc/、oidc/）
│   ├── views/               视图（按板块子目录）
│   │   ├── crawler/  finance/  lingxing/ads/  lingxing/sales/listing/
│   │   ├── nc/  notice/  oidc/  system/  user/
│   ├── tasks/               Celery 任务（nc_sync_tasks、maintenance_tasks）
│   ├── utils/               工具（captcha、fernet_crypto、responses、pagination 等）
│   ├── management/commands/ 管理命令
│   └── urls.py              api_v1 路由分发
├── api_v2/                  任务调度 App（异步执行）
│   ├── models/              任务相关模型（workflow_execution、ai_*、ad_*、listing_tag_*）
│   ├── views/               视图（task、ai_chat、ai_stream、ai_group、ad_*、app）
│   ├── serializers/         序列化器
│   ├── services/            业务服务（ai/、ad_creation/、ad_optimization/、ad_rules/）
│   ├── tasks/               Celery 任务（每个任务一个文件）
│   ├── permissions/         权限类（IsV2Accessible）
│   ├── utils/               工具（task_execution_lock、ai_redis_channel、timezone_utils）
│   └── urls.py              api_v2 路由
├── scripts/                 运维 SQL 脚本
├── tools/                   运维工具
├── templates/               Django 模板（OIDC 登录页等）
├── media/                   上传文件（gitignore）
├── requirements.txt         Python 依赖
├── .env                     环境变量（gitignore，必需）
└── manage.py
```

## 前端 `vue3-element-admin-master/`

```text
vue3-element-admin-master/
├── src/
│   ├── main.ts              应用入口
│   ├── App.vue
│   ├── api/                 网络请求封装（按板块子目录）
│   ├── components/          复用组件（AiAssistant/ 等）
│   ├── composables/         组合式函数（aiAssistant/、auth/、websocket/ 等）
│   ├── constants/           常量
│   ├── directives/          自定义指令
│   ├── enums/               枚举（api/code-enum 等）
│   ├── lang/                国际化
│   ├── layouts/             布局组件
│   ├── plugins/             插件
│   ├── router/              路由
│   ├── store/               Pinia store（modules/）
│   ├── styles/              全局样式
│   ├── types/               TS 类型定义
│   ├── utils/               工具（request、auth 等）
│   └── views/               页面视图（按板块子目录）
├── vite.config.ts           Vite 配置（含 /dev-api 代理）
├── eslint.config.ts         ESLint 配置
├── package.json             依赖与脚本
└── .env.development         开发环境变量
```

## 板块化分组约定

前后端均按业务板块用同名子目录聚合（如 `ads`、`crawler`、`sales/listing`、`lingxing/ads/sp`）。后端子目录 `__init__.py` 显式 `from .xxx import XxxClass` 重导出，使外部可通过 `from api_v1.models import XxxModel` 访问。
