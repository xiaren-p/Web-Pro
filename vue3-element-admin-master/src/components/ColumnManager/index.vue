<template>
  <el-drawer
    v-model="visible"
    title="表头字段显示与排序配置"
    size="880px"
    class="column-config-drawer"
    append-to-body
  >
    <div class="column-config-container">
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
/**
 * 列管理组件：拖拽排序、显示/隐藏、固定列，支持分组。
 */
import { ref, computed, watch } from "vue";
import Sortable from "sortablejs";
import { Search, Rank, ArrowLeft, ArrowRight, Close } from "@element-plus/icons-vue";

/** 列配置项。prop/label/visible 为必填，其余字段按业务需求扩展。 */
export interface ColumnConfig {
  prop: string;
  label: string;
  visible: boolean;
  fixed?: "left" | "right";
  category?: string;
  sortable?: boolean | string;
  minWidth?: number;
  /** 额外业务字段 */
  [key: string]: unknown;
}

/** 分组结构。 */
interface ColumnGroup {
  title: string;
  columns: ColumnConfig[];
}

const props = defineProps<{
  modelValue: boolean;
  columns: ColumnConfig[];
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "save", columns: ColumnConfig[]): void;
  (e: "reset"): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const searchText = ref("");
const internalColumns = ref<ColumnConfig[]>([]);

watch(
  () => props.columns,
  (newCols) => {
    internalColumns.value = JSON.parse(JSON.stringify(newCols));
  },
  { immediate: true, deep: true }
);

const groups = computed(() => {
  const map: Record<string, ColumnConfig[]> = {};
  internalColumns.value.forEach((col) => {
    const cat = col.category || "其他";
    if (!map[cat]) map[cat] = [];
    map[cat].push(col);
  });
  const order = ["基础信息", "库存价格", "销售数据", "其他信息"];
  const result: ColumnGroup[] = [];
  order.forEach((key) => {
    if (map[key]) {
      result.push({ title: key, columns: map[key] });
      delete map[key];
    }
  });
  Object.keys(map).forEach((key) => {
    result.push({ title: key, columns: map[key] });
  });
  return result;
});

const filteredGroups = computed(() => {
  if (!searchText.value) return groups.value;
  const kw = searchText.value.toLowerCase();
  return groups.value
    .map((g) => ({ ...g, columns: g.columns.filter((c) => c.label.toLowerCase().includes(kw)) }))
    .filter((g) => g.columns.length > 0);
});

const visibleColumns = computed(() => internalColumns.value.filter((c) => c.visible).slice(0, 50));

function isGroupAllChecked(group: ColumnGroup): boolean {
  return group.columns.every((c) => c.visible);
}

function toggleGroup(group: ColumnGroup) {
  const checked = !isGroupAllChecked(group);
  group.columns.forEach((c) => {
    c.visible = checked;
  });
}

function toggleFixed(col: ColumnConfig, side: "left" | "right") {
  col.fixed = col.fixed === side ? undefined : side;
}

function resetToDefault() {
  emit("reset");
}

function saveConfig() {
  emit("save", internalColumns.value);
  visible.value = false;
}

const sortListRef = ref<HTMLElement>();
let sortable: Sortable | null = null;

function initSortable() {
  if (!sortListRef.value) return;
  if (sortable) sortable.destroy();
  sortable = Sortable.create(sortListRef.value, {
    animation: 150,
    handle: ".sort-handle",
    onEnd(evt) {
      const { oldIndex, newIndex } = evt;
      if (oldIndex === undefined || newIndex === undefined) return;
      const moved = internalColumns.value.splice(oldIndex, 1)[0];
      internalColumns.value.splice(newIndex, 0, moved);
    },
  });
}

watch(
  visibleColumns,
  () => {
    nextTick(() => initSortable());
  },
  { deep: true }
);
</script>
