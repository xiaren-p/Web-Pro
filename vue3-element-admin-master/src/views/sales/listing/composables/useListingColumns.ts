/**
 * 商品列表页列配置与行选择逻辑 composable。
 *
 * @module useListingColumns
 * @description 列自定义配置（localStorage 缓存）、行选择（含 Shift 批量选择）、列可见性计算。
 */

import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { defaultColumns } from "../constants";

const STORAGE_KEY = "SALES_PRODUCT_LISTING_COLUMNS_V5";

export function useListingColumns() {
  /** 列管理弹窗可见性。 */
  const columnConfigVisible = ref(false);

  /** 初始化列配置（合并本地缓存与默认值）。 */
  function initColumns(): any[] {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        const defaultMap = new Map(defaultColumns.map((c) => [c.prop, c]));
        const cachedProps = new Set<string>();

        const merged = parsed
          .map((c: any) => {
            const def = defaultMap.get(c.prop);
            if (def) {
              cachedProps.add(c.prop);
              return { ...c, category: def.category, label: def.label };
            }
            return null;
          })
          .filter(Boolean);

        const newCols = defaultColumns.filter((c) => !cachedProps.has(c.prop));
        return [...merged, ...newCols];
      } catch (e) {
        console.error("读取列配置失败", e);
      }
    }
    return JSON.parse(JSON.stringify(defaultColumns));
  }

  /** 完整列配置（含隐藏列）。 */
  const columns = ref(initColumns());

  /** 仅可见列。 */
  const tableColumns = computed(() => columns.value.filter((c: any) => c.visible));

  /** 保存列配置到 localStorage。 */
  function handleConfigSave(newColumns: any[]) {
    columns.value = newColumns;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns));
    ElMessage.success("配置已保存");
  }

  /** 恢复默认列配置。 */
  function handleConfigReset() {
    columns.value = JSON.parse(JSON.stringify(defaultColumns));
    localStorage.removeItem(STORAGE_KEY);
    ElMessage.success("已恢复默认配置");
  }

  // ── Shift 批量选择 ──────────────────────────────────────────────────────────────
  const isShiftDown = ref(false);

  function onShiftKeyDown(e: KeyboardEvent) {
    if (e.key === "Shift") isShiftDown.value = true;
  }
  function onShiftKeyUp(e: KeyboardEvent) {
    if (e.key === "Shift") isShiftDown.value = false;
  }

  onMounted(() => {
    window.addEventListener("keydown", onShiftKeyDown);
    window.addEventListener("keyup", onShiftKeyUp);
  });
  onUnmounted(() => {
    window.removeEventListener("keydown", onShiftKeyDown);
    window.removeEventListener("keyup", onShiftKeyUp);
  });

  return {
    columnConfigVisible,
    columns,
    tableColumns,
    handleConfigSave,
    handleConfigReset,
    isShiftDown,
  };
}
