import type { RouteRecordRaw } from "vue-router";
import { constantRoutes } from "@/router";
import { store } from "@/store";
import router from "@/router";

import { MenuAPI, type RouteVO } from "@/api/menu";
const modules = import.meta.glob("../../views/**/**.vue");
const Layout = () => import("../../layouts/index.vue");

// 构建大小写不敏感的映射表，用于兼容 Windows/Linux 文件系统差异或用户输入的大小写不一致
const lowerCaseModules: Record<string, any> = {};
Object.keys(modules).forEach((key) => {
  lowerCaseModules[key.toLowerCase()] = modules[key];
});

export const usePermissionStore = defineStore("permission", () => {
  // 所有路由（静态路由 + 动态路由）
  const routes = ref<RouteRecordRaw[]>([]);
  // 混合布局的左侧菜单路由
  const mixLayoutSideMenus = ref<RouteRecordRaw[]>([]);
  // 动态路由是否已生成
  const isRouteGenerated = ref(false);

  /** 生成动态路由 */
  async function generateRoutes(): Promise<RouteRecordRaw[]> {
    try {
      const data = await MenuAPI.getRoutes(); // 获取当前登录人的菜单路由
      const dynamicRoutes = transformRoutes(data);

      routes.value = [...constantRoutes, ...dynamicRoutes];
      isRouteGenerated.value = true;

      return dynamicRoutes;
    } catch (error) {
      // 路由生成失败，重置状态
      isRouteGenerated.value = false;
      throw error;
    }
  }

  /** 设置混合布局左侧菜单 */
  const setMixLayoutSideMenus = (parentPath: string) => {
    const parentMenu = routes.value.find((item) => item.path === parentPath);
    mixLayoutSideMenus.value = parentMenu?.children || [];
  };

  /** 重置路由状态 */
  const resetRouter = () => {
    // 移除动态添加的路由
    const constantRouteNames = new Set(constantRoutes.map((route) => route.name).filter(Boolean));
    routes.value.forEach((route) => {
      if (route.name && !constantRouteNames.has(route.name)) {
        router.removeRoute(route.name);
      }
    });

    // 重置所有状态
    routes.value = [...constantRoutes];
    mixLayoutSideMenus.value = [];
    isRouteGenerated.value = false;
  };

  return {
    routes,
    mixLayoutSideMenus,
    isRouteGenerated,
    generateRoutes,
    setMixLayoutSideMenus,
    resetRouter,
  };
});

/**
 * 转换后端路由数据为Vue Router配置
 * 处理组件路径映射和Layout层级嵌套
 */
// 需要在前端强制排除的动态路由（后端暂未下线的情况下做临时隐藏）
// 可以根据 path / name / meta.title 三种方式匹配
const EXCLUDED_ROUTE_PATHS = new Set([
  "/system/dict-item",
  "/system/dictItem",
  "/system/dict/item",
]);
const EXCLUDED_ROUTE_NAMES = new Set(["DictItem", "DictItemManage", "DictItemManagement"]);
const EXCLUDED_ROUTE_TITLES = new Set(["字典项管理", "字典项", "字典项维护"]);

const transformRoutes = (routes: RouteVO[], isTopLevel: boolean = true): RouteRecordRaw[] => {
  return routes
    .map((route) => {
      const { component, children, ...args } = route;
      const processedComponent = isTopLevel || component !== "Layout" ? component : undefined;
      const normalizedRoute = { ...args } as RouteRecordRaw;

      // 无效路径防护：仅对顶级路由要求以 "/" 开头，子路由可为相对路径
      if (isTopLevel && (!route.path || !route.path.startsWith("/"))) {
        return undefined as any;
      }

      // 命中排除条件：不删除路由，仅隐藏菜单项
      if (
        (route.path && EXCLUDED_ROUTE_PATHS.has(route.path)) ||
        (route.name && EXCLUDED_ROUTE_NAMES.has(route.name)) ||
        (route.meta?.title && EXCLUDED_ROUTE_TITLES.has(route.meta.title))
      ) {
        normalizedRoute.meta = { ...(normalizedRoute.meta || {}), hidden: true } as any;
      }

      if (!processedComponent) {
        // 后端未提供组件路径时，使用 404 作为兜底，避免出现空组件导致路由无法匹配
        normalizedRoute.component = modules[`../../views/error/404.vue`];
      } else {
        if (processedComponent === "Layout") {
          normalizedRoute.component = Layout;
        } else {
          const directPath = `../../views/${processedComponent}.vue`;
          const indexPath = `../../views/${processedComponent}/index.vue`;

          // 优先尝试精确匹配，如果失败则尝试忽略大小写匹配
          const componentLoader =
            modules[directPath] ||
            modules[indexPath] ||
            lowerCaseModules[directPath.toLowerCase()] ||
            lowerCaseModules[indexPath.toLowerCase()];

          normalizedRoute.component = componentLoader || modules[`../../views/error/404.vue`];
        }
      }

      if (children && children.length > 0) {
        const childTransformed = transformRoutes(children, false);
        if (childTransformed.length > 0) {
          normalizedRoute.children = childTransformed;
        }
      }
      return normalizedRoute;
    })
    .filter((r): r is RouteRecordRaw => !!r);
};

/** 非组件环境使用权限store */
export function usePermissionStoreHook() {
  return usePermissionStore(store);
}
