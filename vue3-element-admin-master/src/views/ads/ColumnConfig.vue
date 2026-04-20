<template>
  <el-dialog
    v-model="visible"
    width="900px"
    class="column-config-dialog"
    :show-close="false"
    align-center
    destroy-on-close
  >
    <template #header>
      <div class="dialog-header">
        <div class="header-left">
          <el-select v-model="templateName" placeholder="模板名称" style="width: 200px">
            <el-option label="默认模板" value="default" />
          </el-select>
          <el-button type="primary" link class="ml-4">管理模板</el-button>
        </div>
        <div class="header-right">
          <el-button type="primary" link>保存为常用模板</el-button>
        </div>
      </div>
    </template>

    <div class="config-body">
      <div class="left-panel">
        <div class="section">
          <div class="section-title">
            <span class="fw-bold text-black">设置</span>
            <el-button type="primary" link @click="toggleSelectAll('setting')">全选</el-button>
          </div>
          <el-checkbox-group v-model="selectedColumns" class="checkbox-grid">
            <el-checkbox v-for="item in settingOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="section">
          <div class="section-title">
            <span class="fw-bold text-black">业绩</span>
            <el-button type="primary" link @click="toggleSelectAll('performance')">全选</el-button>
          </div>
          <el-checkbox-group v-model="selectedColumns" class="checkbox-grid">
            <el-checkbox v-for="item in performanceOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="section">
          <div class="section-title">
            <span class="fw-bold text-black">转化</span>
            <el-button type="primary" link @click="toggleSelectAll('conversion')">全选</el-button>
          </div>
          <el-checkbox-group v-model="selectedColumns" class="checkbox-grid">
            <el-checkbox v-for="item in conversionOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </div>

      <div class="right-panel">
        <div class="search-box">
          <el-input v-model="searchText" placeholder="搜索" clearable />
        </div>
        <div class="list-container">
          <div class="list-tip text-gray-400 text-xs mb-2">最多可固定7项</div>
          <VueDraggable
            v-model="rightList"
            class="drag-list"
            handle=".drag-handle"
            :animation="200"
          >
            <div
              v-for="element in rightList"
              v-show="
                !searchText || element.label.toLowerCase().includes(searchText.trim().toLowerCase())
              "
              :key="element.value"
              class="drag-item"
              :class="{ 'is-pinned': isPinned(element) }"
            >
              <div class="item-left">
                <el-icon class="drag-handle mr-2 text-gray-400 cursor-move"><Grid /></el-icon>
                <span>{{ element.label }}</span>
              </div>
              <div class="item-actions">
                <el-icon class="action-icon" title="移除" @click.stop="removeItem(element)">
                  <CircleClose />
                </el-icon>
                <el-icon class="action-icon" title="置顶" @click.stop="moveToTop(element)">
                  <Top />
                </el-icon>
                <i
                  class="action-icon pin-icon"
                  :class="{ 'is-pinned': isPinned(element) }"
                  title="固定"
                  @click.stop="togglePin(element)"
                >
                  <svg viewBox="0 0 1024 1024" width="14" height="14">
                    <path
                      d="M512 85.333333c-84.906667 0-153.6 68.693333-153.6 153.6v124.586667L241.152 505.685333A85.333333 85.333333 0 0 0 213.333333 560.64v34.133333c0 47.104 38.229333 85.333333 85.333333 85.333334h170.666667v216.746666l42.666667 42.666667 42.666667-42.666667v-216.746666h170.666666c47.104 0 85.333333-38.229333 85.333334-85.333334v-34.133333a85.333333 85.333333 0 0 0-27.818667-54.954667L665.6 363.52V238.933333c0-84.906667-68.693333-153.6-153.6-153.6z"
                      fill="currentColor"
                    ></path>
                  </svg>
                </i>
              </div>
            </div>
          </VueDraggable>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div>
          <el-button type="primary" @click="applyTemplate('default')">默认模板</el-button>
          <el-button @click="applyTemplate('compact')">精简模板</el-button>
        </div>
        <div>
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" @click="saveConfig">保存</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Grid, CircleClose, Top } from "@element-plus/icons-vue";
import { VueDraggable } from "vue-draggable-plus";
import { ElMessage } from "element-plus";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits(["update:modelValue", "save"]);

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const templateName = ref("default");
const searchText = ref("");

// Options as requested (Only checked ones from the image)
const settingOptions = [
  { label: "服务状态", value: "service_status" },
  { label: "广告组合", value: "portfolio_name" },
  { label: "竞价策略", value: "bidding_type" },
  { label: "预算", value: "budget" },
  { label: "超预算时间", value: "last_over_budget_at" },
  { label: "开始日期", value: "start_date" },
  { label: "标签", value: "tags" },
];

const conversionOptions = [
  { label: "IS", value: "top_of_search_impression_share" },
  { label: "广告销售额", value: "sales" },
  { label: "广告销售额%", value: "sales_percent" },
  { label: "直接销售额", value: "direct_sales" },
  { label: "ACoS", value: "acos" },
  { label: "ROAS", value: "roas" },
  { label: "广告订单", value: "orders" },
  { label: "直接订单", value: "direct_orders" },
  { label: "CVR", value: "cvr" },
  { label: "广告笔单价", value: "unit_price" },
  { label: "广告销量", value: "ad_units" },
];

const performanceOptions = [
  { label: "曝光量", value: "impressions" },
  { label: "曝光%", value: "impressions_percent" },
  { label: "点击", value: "clicks" },
  { label: "点击%", value: "clicks_percent" },
  { label: "CTR", value: "ctr" },
  { label: "CPC", value: "cpc" },
  { label: "花费", value: "spends" },
  { label: "花费%", value: "spends_percent" },
  { label: "CPA", value: "cpa" },
];

const allOptions = [...settingOptions, ...performanceOptions, ...conversionOptions];

// Initialize all checked since user said those are the only ones left and they were checked
const selectedColumns = ref(allOptions.map((o) => o.value));

// The right list based on selected, filtered by search text
const rightList = ref([...allOptions]);

// Sync rightList when selectedColumns changes
watch(
  () => [...selectedColumns.value],
  (newVal) => {
    // Add missing ones to the end
    newVal.forEach((val) => {
      if (!rightList.value.find((r) => r.value === val)) {
        const opt = allOptions.find((o) => o.value === val);
        if (opt) rightList.value.push(opt);
      }
    });
    // Remove unchecked ones
    rightList.value = rightList.value.filter((r) => newVal.includes(r.value));
  },
  { deep: true, immediate: true }
);

// Notice: In real scenario, `rightList` is also filtered by `searchText` before displaying,
// However, `vue-draggable-plus` needs the raw array to operate properly on sorts.
// We'll keep it simple: we aren't heavily implementing the search filter logic here to avoid messing up dragging index.

function toggleSelectAll(type: "setting" | "conversion" | "performance") {
  const options =
    type === "setting"
      ? settingOptions
      : type === "conversion"
        ? conversionOptions
        : performanceOptions;
  const values = options.map((o) => o.value);
  const allSelected = values.every((v) => selectedColumns.value.includes(v));

  if (allSelected) {
    selectedColumns.value = selectedColumns.value.filter((v) => !values.includes(v));
  } else {
    const toAdd = values.filter((v) => !selectedColumns.value.includes(v));
    selectedColumns.value.push(...toAdd);
  }
}

function applyTemplate(tpl: string) {
  if (tpl === "default") {
    selectedColumns.value = allOptions.map((o) => o.value);
  } else if (tpl === "compact") {
    selectedColumns.value = ["serviceStatus", "adsSales", "acos", "roas"];
  }
}

const pinnedList = ref<string[]>([]);

function removeItem(element: any) {
  selectedColumns.value = selectedColumns.value.filter((v) => v !== element.value);
}

function moveToTop(element: any) {
  const idx = rightList.value.findIndex((r) => r.value === element.value);
  if (idx > 0) {
    const [removed] = rightList.value.splice(idx, 1);
    rightList.value.unshift(removed);
  }
}

function isPinned(element: any) {
  return pinnedList.value.includes(element.value);
}

function togglePin(element: any) {
  const idx = pinnedList.value.indexOf(element.value);
  if (idx > -1) {
    pinnedList.value.splice(idx, 1);
  } else {
    if (pinnedList.value.length >= 7) {
      ElMessage.warning("最多只能固定7项");
      return;
    }
    pinnedList.value.push(element.value);
  }
}

function saveConfig() {
  const finalColumns = rightList.value.map((col) => ({
    ...col,
    fixed: pinnedList.value.includes(col.value) ? "left" : false,
  }));
  emit("save", finalColumns);
  visible.value = false;
}
</script>

<style scoped>
.column-config-dialog :deep(.el-dialog__header) {
  padding: 12px 20px;
  margin-right: 0;
  border-bottom: 1px solid #e4e7ed;
}
.column-config-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
}

.config-body {
  display: flex;
  height: 520px;
  overflow: hidden;
}
.left-panel {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  border-right: 1px solid #e4e7ed;
}
.left-panel::-webkit-scrollbar,
.list-container::-webkit-scrollbar {
  width: 6px;
}
.left-panel::-webkit-scrollbar-thumb,
.list-container::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
}
.left-panel::-webkit-scrollbar-track,
.list-container::-webkit-scrollbar-track {
  background: transparent;
}

.right-panel {
  display: flex;
  flex-direction: column;
  width: 270px;
  background-color: #f7f8fa;
}

.section {
  margin-bottom: 32px;
}
.section:last-child {
  margin-bottom: 0;
}
.section-title {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}
.text-black {
  color: #303133;
}
.fw-bold {
  font-size: 15px;
  font-weight: 700;
}
.section-title :deep(.el-button) {
  font-size: 14px;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  row-gap: 22px;
  column-gap: 8px;
}
.checkbox-grid :deep(.el-checkbox) {
  height: auto;
  margin-right: 0;
  font-weight: normal;
  color: #606266;
}
.checkbox-grid :deep(.el-checkbox__label) {
  padding-left: 8px;
  font-size: 14px;
}
/* 选中时保持默认文字颜色，不改变为蓝色 */
.checkbox-grid :deep(.el-checkbox.is-checked .el-checkbox__label) {
  color: #606266;
}

.search-box {
  padding: 0;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}
.search-box :deep(.el-input__wrapper) {
  padding: 4px 12px;
  border-radius: 0;
  box-shadow: none !important;
}

.list-container {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
}

.drag-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  margin-bottom: 2px;
  font-size: 13px;
  color: #333;
  border-radius: 4px;
}
.item-left {
  display: flex;
  align-items: center;
}
.item-actions {
  display: none;
  gap: 10px;
  align-items: center;
  padding-right: 4px;
}
.drag-item:hover .item-actions {
  display: flex;
}
.action-icon {
  font-size: 14px;
  color: #909399;
  cursor: pointer;
}
.action-icon:hover {
  color: #409eff;
}
.pin-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.pin-icon.is-pinned {
  color: #409eff; /* 选中图钉变为高亮蓝 */
}
.drag-item.is-pinned {
  background: #f0f7ff; /* 固定的列浅蓝背景 */
}
.drag-item:hover {
  background: #e4e7ed;
}
.drag-item:hover.is-pinned {
  background: #dbeafe; /* hover时叠加更深的浅蓝 */
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 4px;
}
</style>
