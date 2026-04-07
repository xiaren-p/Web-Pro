<template>
  <div class="login-wrapper">
    <!-- 右侧切换主题、语言按钮 -->
    <div class="action-bar">
      <el-tooltip :content="t('login.themeToggle')" placement="bottom">
        <CommonWrapper>
          <DarkModeSwitch />
        </CommonWrapper>
      </el-tooltip>
    </div>

    <!-- 背景波浪图 -->
    <el-image :src="bg" class="wave" />

    <!-- 登录页主体 -->
    <div class="login-container">
      <div class="img">
        <LoginIllustration />
      </div>

      <div class="login-box">
        <div class="login-form">
          <!-- logo -->
          <div class="avatar">
            <el-image :src="loginLogo" style="width: 140px; max-width: 40vw" />
          </div>

          <!-- 标题 -->
          <!-- <h2 class="title">
            {{ defaultSettings.title }}
          </h2> -->

          <!-- 组件切换 -->
          <transition name="fade-slide" mode="out-in">
            <component :is="formComponents[component]" v-model="component" class="w-full" />
          </transition>
        </div>

        <!-- 底部版权 -->
        <div class="footer">Copyright ©2026 佛山市韩丽舍装饰设计工程有限公司.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import loginLogo from "@/assets/login_logo.png";
import bg from "@/assets/images/login-bg-3.png";
// removed unused import
import CommonWrapper from "@/components/CommonWrapper/index.vue";
import DarkModeSwitch from "@/components/DarkModeSwitch/index.vue";
import LoginIllustration from "./components/LoginIllustration.vue";

type LayoutMap = "login";

const t = useI18n().t;

const component = ref<LayoutMap>("login"); // 仅保留登录组件
const formComponents = {
  login: defineAsyncComponent(() => import("./components/Login.vue")),
};
</script>

<style lang="scss" scoped>
.login-wrapper {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(to bottom, #f9fcff 0%, #f5f9fd 100%);
}

.login-container {
  position: relative;
  z-index: 10;
  display: flex;
  width: 100%;
  height: 100%;
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  z-index: 1;
  width: 100%;
  height: auto;
  pointer-events: none;
  transform: translateX(-50px);
}

.img {
  position: relative;
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
}

.login-box {
  position: relative; // Needed for footer absolute positioning
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
}

.login-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 400px;
  max-width: 90%;
  padding: 40px;
}

.avatar {
  margin-bottom: 20px;
}

.title {
  margin-bottom: 30px;
  font-size: 24px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}

.action-bar {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
}

.footer {
  position: absolute;
  bottom: 10px;
  z-index: 10;
  width: 100%;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

/* fade-slide */
.fade-slide-leave-active,
.fade-slide-enter-active {
  transition: all 0.3s;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

@media (max-width: 768px) {
  .img {
    display: none;
  }
  .login-box {
    width: 100%;
  }
}
</style>

<!-- 全局样式：根据 html.dark 切换背景图片色调 -->
<style lang="scss">
html.dark .login-wrapper .wave {
  filter: brightness(0.5) saturate(0.8) contrast(0.9);
  transition: filter 0.3s ease;
}

/* 将页面中原本是白色或透明的区域在暗色模式下调整为深色调 */
html.dark .login-wrapper {
  background: linear-gradient(to bottom, #07101a 0%, #071017 100%);
}

html.dark .login-wrapper .login-box {
  background: transparent;
}

html.dark .login-wrapper .login-form {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
  transition:
    background 0.25s ease,
    box-shadow 0.25s ease;
}

html.dark .login-wrapper .avatar img,
html.dark .login-wrapper .title,
html.dark .login-wrapper .footer {
  color: rgba(220, 220, 242, 0.9);
}

/* 调整表单内文字与控件的可读性 */
html.dark .login-wrapper .login-form .el-input__inner,
html.dark .login-wrapper .login-form .el-button {
  color: var(--el-text-color-primary, #e6eef8);
  background-color: rgba(255, 255, 255, 0.02);
}
</style>
