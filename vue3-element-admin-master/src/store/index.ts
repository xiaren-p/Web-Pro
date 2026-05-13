import type { App } from "vue";
import { createPinia } from "pinia";

const store = createPinia();

// 全局注册 store
export function setupStore(app: App<Element>) {
  app.use(store);
}

/**
 * Pinia Store 统一出口：显式封装所有模块，禁止使用 `export *` 桶文件。
 */
export { useAppStore, useAppStoreHook } from "./modules/app-store";
export { usePermissionStore, usePermissionStoreHook } from "./modules/permission-store";
export { useSettingsStore } from "./modules/settings-store";
export { useTagsViewStore } from "./modules/tags-view-store";
export { useUserStore, useUserStoreHook } from "./modules/user-store";
export { useDictStore, useDictStoreHook } from "./modules/dict-store";
export { store };
