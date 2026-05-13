<template>
  <el-drawer
    v-model="visible"
    title="表头字段显示与排序配置"
    size="880px"
    class="column-config-drawer"
    append-to-body
  >
    <div class="column-config-container">
      <!-- 左侧：分组选择 -->
      <div class="config-left">
        <div class="search-box">
          <el-input v-model="searchText" placeholder="搜索" :prefix-icon="Search" clearable />
        </div>

        <el-scrollbar class="checkbox-groups">
          <div v-for="group in filteredGroups" :key="group.title" class="group-section">
            <div class="group-header">
              <span class="title">{{ group.title }}</span>
              <el-button type="primary" link size="small" @click="toggleGroup(group)">
                {{ isGroupAllChecked(group) ? "取消" : "全选" }}
              </el-button>
            </div>
            <div class="group-items">
              <el-checkbox
                v-for="col in group.columns"
                :key="col.prop"
                v-model="col.visible"
                :label="col.label"
                size="small"
                class="group-item-checkbox"
              />
            </div>
          </div>
        </el-scrollbar>
      </div>

      <!-- 右侧：排序 -->
      <div class="config-right">
        <div class="selected-count">
          已选
          <span>({{ visibleColumns.length }})</span>
          <span v-if="visibleColumns.length > 50" class="limit-tip">最多50项</span>
        </div>

        <div class="sort-tip">点击可拖拽排序</div>

        <el-scrollbar>
          <div ref="sortListRef" class="sort-list">
            <div
              v-for="(col, index) in visibleColumns"
              :key="col.prop"
              class="sort-item"
              :data-id="col.prop"
            >
              <div class="sort-handle">
                <el-icon class="drag-icon"><Rank /></el-icon>
                <span class="sort-index">{{ index + 1 }}</span>
                <span class="sort-label">{{ col.label }}</span>
              </div>
              <div class="sort-actions">
                <el-icon
                  class="action-icon"
                  :class="{ active: col.fixed === 'left' }"
                  title="固定在左侧"
                  @click="toggleFixed(col, 'left')"
                >
                  <ArrowLeft />
                </el-icon>
                <el-icon
                  class="action-icon"
                  :class="{ active: col.fixed === 'right' }"
                  title="固定在右侧"
                  @click="toggleFixed(col, 'right')"
                >
                  <ArrowRight />
                </el-icon>
                <el-icon class="action-icon delete-icon" @click="col.visible = false">
                  <Close />
                </el-icon>
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <el-button @click="resetToDefault">恢复默认</el-button>
        <div>
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" @click="saveConfig">保存并应用</el-button>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import Sortable from "sortablejs";
import { Search, Rank, ArrowLeft, ArrowRight, Close } from "@element-plus/icons-vue";

const props = defineProps<{
  modelValue: boolean;
  columns: any[]; // 所有列配置对象
}>();

const emit = defineEmits(["update:modelValue", "save", "reset"]);

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const searchText = ref("");
const internalColumns = ref<any[]>([]);

// 初始化内部数据
watch(
  () => props.columns,
  (newCols) => {
    // 深拷贝以避免直接修改父组件数据
    internalColumns.value = JSON.parse(JSON.stringify(newCols));
  },
  { immediate: true, deep: true }
);

// 分组逻辑
const groups = computed(() => {
  const map: Record<string, any[]> = {};
  internalColumns.value.forEach((col) => {
    const cat = col.category || "其他";
    if (!map[cat]) map[cat] = [];
    map[cat].push(col);
  });

  // 按照特定顺序排序分组
  const order = ["基础信息", "库存价格", "销售数据", "其他信息"];
  const result: any[] = [];

  order.forEach((key) => {
    if (map[key]) {
      result.push({ title: key, columns: map[key] });
      delete map[key];
    }
  });

  // 剩下的分组
  Object.keys(map).forEach((key) => {
    result.push({ title: key, columns: map[key] });
  });

  return result;
});

const filteredGroups = computed(() => {
  if (!searchText.value) return groups.value;
  const text = searchText.value.toLowerCase();

  return groups.value
    .map((g) => {
      const cols = g.columns.filter((c: any) => c.label.includes(text));
      if (cols.length > 0) {
        return { ...g, columns: cols };
      }
      return null;
    })
    .filter(Boolean);
});

// 已选列 (用于排序列表)
// 注意：排序列表的顺序决定了最终表格的顺序。
// 所以我们需要维护一个顺序列表。
// 这里的 internalColumns 本身就是有序的。
const visibleColumns = computed(() => {
  return internalColumns.value.filter((c) => c.visible);
});

function isGroupAllChecked(group: any) {
  return group.columns.every((c: any) => c.visible);
}

function toggleGroup(group: any) {
  const allChecked = isGroupAllChecked(group);
  group.columns.forEach((c: any) => (c.visible = !allChecked));
}

function toggleFixed(col: any, direction: "left" | "right") {
  if (col.fixed === direction) {
    col.fixed = false;
  } else {
    col.fixed = direction;
  }
}

// 拖拽排序
const sortListRef = ref<HTMLElement>();
let sortableInstance: Sortable | null = null;

watch(visible, async (val) => {
  if (val) {
    await nextTick();
    if (sortListRef.value && !sortableInstance) {
      sortableInstance = new Sortable(sortListRef.value, {
        animation: 150,
        handle: ".sort-handle",
        onEnd: (evt) => {
          const { oldIndex, newIndex } = evt;
          if (oldIndex === undefined || newIndex === undefined) return;

          // 获取当前可见列表的 item
          const visibleCols = internalColumns.value.filter((c) => c.visible);

          // 计算在完整列表中的 移动逻辑比较复杂，简单起见：
          // 我们先把 visibleCols 重新排序
          visibleCols.splice(newIndex, 0, visibleCols.splice(oldIndex, 1)[0]);

          // 然后把不可见的列 找出来
          const hiddenCols = internalColumns.value.filter((c) => !c.visible);

          // 重新组合：为了保持“已选列的顺序就是用户排的顺序”，
          // 我们把排好序的 visibleCols 放在前面 (或者按照原逻辑混合，但通常用户只想排可见的)
          // 简单策略：visibleCols 排前面，hiddenCols 排后面，或者 interleaved 不变？
          // 通常列配置里，显示的列通过拖拽改变的是它们之间的相对顺序。

          // 重建 internalColumns：按照新的 visibleCols 顺序 + hiddenCols
          // 这样会导致隐藏列跑到最后，但这通常是可以接受的
          internalColumns.value = [...visibleCols, ...hiddenCols];
        },
      });
    }
  }
});

function saveConfig() {
  emit("save", JSON.parse(JSON.stringify(internalColumns.value)));
  visible.value = false;
}

function resetToDefault() {
  emit("reset");
  visible.value = false;
}
</script>

<style scoped>
.column-config-container {
  display: flex;
  height: calc(100vh - 140px);
  overflow: hidden;
  font-size: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
}

.config-left {
  display: flex;
  flex-direction: column;
  width: 62%;
  background-color: #fff;
}

.search-box {
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--el-border-color-lighter) inset;
}
.search-box :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-color-primary-light-3) inset;
}

.checkbox-groups {
  flex: 1;
}

.group-section {
  padding: 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.group-section:last-child {
  border-bottom: none;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: bold;
  color: var(--el-text-color-primary);
  background-color: var(--el-fill-color-light);
  border-left: 4px solid var(--el-color-primary);
  border-radius: 8px;
}

.group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 0;
}

.group-item-checkbox {
  box-sizing: border-box;
  width: 33.33%;
  padding: 6px 10px;
  margin-right: 0;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}
.group-item-checkbox:hover {
  background-color: var(--el-fill-color);
}

/* 优化 checkbox 的截断与展示 */
:deep(.el-checkbox__label) {
  width: calc(100% - 22px);
  padding-left: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 15px;
  vertical-align: middle;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.config-right {
  display: flex;
  flex-direction: column;
  width: 38%;
  background-color: var(--el-color-info-light-9);
  border-left: 1px solid var(--el-border-color-light);
}

.selected-count {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  font-size: 14px;
  font-weight: bold;
  color: var(--el-text-color-primary);
  background-color: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.limit-tip {
  font-size: 12px;
  font-weight: normal;
  color: var(--el-text-color-secondary);
}

.sort-tip {
  padding: 12px 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.sort-list {
  padding: 10px 20px;
}

.sort-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin-bottom: 10px;
  background-color: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
  transition: all 0.2s ease;
}
.sort-item:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.sort-handle {
  display: flex;
  flex: 1;
  align-items: center;
  overflow: hidden;
  cursor: grab;
}
.sort-handle:active {
  cursor: grabbing;
}

.drag-icon {
  margin-right: 12px;
  font-size: 18px;
  color: var(--el-text-color-placeholder);
  transition: color 0.2s;
}
.sort-item:hover .drag-icon {
  color: var(--el-color-primary-light-3);
}

.sort-index {
  display: inline-block;
  width: 28px;
  font-family: monospace;
  font-size: 13px;
  font-weight: 800;
  color: var(--el-text-color-secondary);
}

.sort-label {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.sort-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  border-radius: 4px;
  opacity: 0.4;
  transition: all 0.2s;
}

.action-icon:hover {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
  opacity: 1 !important;
  transform: scale(1.05);
}

.sort-item:hover .action-icon {
  opacity: 0.7;
}

.action-icon.active {
  color: #fff;
  background-color: var(--el-color-primary);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.3);
  opacity: 1;
}

.delete-icon:hover {
  color: #fff !important;
  background-color: var(--el-color-danger) !important;
  box-shadow: 0 2px 6px rgba(245, 108, 108, 0.3);
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
