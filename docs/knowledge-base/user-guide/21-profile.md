# 个人中心

个人中心展示与编辑当前登录用户的个人信息。后端端点前缀 `/api/v1/users`。

## 入口

点击右上角用户头像 → 个人中心（路由 `/profile`）。

## 基本信息

查看用户名、昵称、部门、岗位、创建时间。

## 编辑个人信息

`PUT /users/profile`：修改昵称、手机、头像、部门、性别、邮箱。

## 绑定手机

1. 输入手机号。
2. `POST /users/mobile/code`：发送手机验证码（仅校验参数，短信渠道待接入）。
3. 输入验证码。
4. `PUT /users/mobile`：绑定手机号。

## 绑定邮箱

1. 输入邮箱。
2. `POST /users/email/code`：发送邮箱验证码。
3. 输入验证码。
4. `PUT /users/email`：绑定邮箱。

## 修改头像

`POST /users/avatar`：上传图片（JPEG / PNG / WEBP，≤5MB）。

- Magic Number 三重校验确保文件类型真实。
- 压缩至 512×512 JPEG。
- 旧文件自动清理。
- 保存后同步到 Nextcloud。
- 未自定义头像的用户使用预设头像（`preset:01`~`preset:12`）。

## 修改密码

`PUT /users/password`：输入旧密码与新密码完成修改。

## 通用图片上传

`POST /users/upload-image`：通用图片上传（≤2MB），生成缩略图，返回 URL / 宽高 / 尺寸 / 建议裁剪区域。供需要图片上传的其他模块复用。

## 验证码

- 图形验证码在登录页使用（`GET /auth/captcha`）。
- 手机 / 邮箱验证码在个人中心绑定时使用。
- 开发环境可配置万能验证码绕过（`ALLOW_CAPTCHA_BYPASS=true` + `CAPTCHA_MASTER_CODE`），生产环境务必关闭。
