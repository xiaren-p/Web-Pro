/**
 * 项目 Composable 统一导出入口。
 *
 * 涵盖 WebSocket 通信、布局控制、设备检测、Token 刷新等跨组件复用逻辑。
 */
export { useStomp } from "./websocket/useStomp";
export { useDictSync } from "./websocket/useDictSync";
export type { DictMessage } from "./websocket/useDictSync";
export { useOnlineCount } from "./websocket/useOnlineCount";
export { useTokenRefresh } from "./auth/useTokenRefresh";

export { useLayout } from "./layout/useLayout";
export { useLayoutMenu } from "./layout/useLayoutMenu";
export { useDeviceDetection } from "./layout/useDeviceDetection";
