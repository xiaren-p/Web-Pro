<template>
  <div class="filters-container">
    <!-- Row 1: 所有筛选下拉项 -->
    <div class="filter-row filter-row-main">
      <FsSelect
        v-model="local.countries"
        size="small"
        class="filter-item w-80"
        :options="countries"
        multiple
        placeholder="国家"
      />
      <FsSelect
        v-model="local.profiles"
        size="small"
        class="filter-item w-160"
        :options="profiles"
        :show-select-all="false"
        multiple
        filterable
        placeholder="选择店铺"
      />
      <el-date-picker
        v-model="local.range"
        size="small"
        class="filter-item date-picker"
        type="daterange"
        start-placeholder="开始"
        end-placeholder="结束"
        range-separator="-"
        value-format="YYYY-MM-DD"
        unlink-panels
      />
      <FsSelect
        v-model="local.adsTypes"
        size="small"
        class="filter-item w-100"
        :options="adsTypes"
        multiple
        placeholder="广告类型"
      />
      <FsSelect
        v-model="local.portfolios"
        size="small"
        class="filter-item w-100"
        :options="portfolios"
        multiple
        filterable
        remote
        reserve-keyword
        :remote-method="remoteSearchPortfolio"
        placeholder="广告组合"
      />
      <div class="filter-item input-group-seamless">
        <el-select
          v-model="local.asinSearchType"
          size="small"
          class="seamless-left w-110"
          placeholder="ASIN查询"
        >
          <el-option label="按ASIN/MSKU查询" value="sku" />
          <el-option label="按父ASIN查询" value="parent_asin" />
        </el-select>
        <FsSelect
          v-model="local.skus"
          size="small"
          :options="skuOptions"
          multiple
          remote
          :remote-method="remoteSearchSku"
          placeholder="MSKU"
          :show-only="true"
          class="seamless-right w-110"
        />
        <el-button
          v-if="local.skus?.length"
          size="small"
          :icon="Close"
          class="btn-msku-clear"
          title="清空MSKU"
          @click="clearField('skus')"
        />
      </div>
      <FsSelect
        v-model="local.campaignStatus"
        size="small"
        class="filter-item w-80"
        :options="campaignStatuses"
        multiple
        placeholder="状态"
      />
      <FsSelect
        v-model="local.serviceStatus"
        size="small"
        class="filter-item w-100"
        :options="serviceStatuses"
        multiple
        placeholder="服务状态"
      />
    </div>

    <!-- Row 2: 标签/负责人/搜索/操作 -->
    <div class="filter-row filter-row-secondary">
      <FsSelect
        v-model="local.biddingType"
        size="small"
        class="filter-item w-100"
        :options="biddingTypes"
        placeholder="竞价策略"
        clearable
      />
      <FsSelect
        v-model="local.tags"
        size="small"
        class="filter-item w-110"
        :options="tagsList"
        multiple
        placeholder="活动标签"
      />
      <FsSelect
        v-model="local.owners"
        size="small"
        class="filter-item w-100"
        :options="owners"
        multiple
        placeholder="负责人"
      />
      <el-input
        v-model="local.campaignName"
        size="small"
        class="filter-item campaign-input"
        placeholder="请输入广告活动"
        :prefix-icon="Search"
        clearable
      />
      <div class="filter-actions">
        <el-button size="small" class="btn-template" @click="openTemplates">
          <el-icon style="margin-right: 4px"><Filter /></el-icon>
          筛选模板
        </el-button>
        <el-button
          type="primary"
          size="small"
          :icon="Search"
          class="btn-icon-only"
          @click="onSearch"
        />
        <el-button size="small" :icon="Brush" class="btn-icon-only" @click="onReset" />
      </div>
    </div>

    <div v-if="hasSelected" class="filter-tags-row">
      <el-tag
        v-if="local.countries?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('countries')"
      >
        {{ formatTagText("国家", local.countries, countries) }}
      </el-tag>
      <el-tag
        v-if="local.profiles?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('profiles')"
      >
        {{ formatTagText("店铺", local.profiles, profiles) }}
      </el-tag>
      <el-tag
        v-if="local.adsTypes?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('adsTypes')"
      >
        {{ formatTagText("广告类型", local.adsTypes, adsTypes) }}
      </el-tag>
      <el-tag
        v-if="local.portfolios?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('portfolios')"
      >
        {{ formatTagText("组合", local.portfolios, portfolios) }}
      </el-tag>
      <el-tag
        v-if="local.skus?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('skus')"
      >
        {{ formatTagText("MSKU", local.skus, skuOptions) }}
      </el-tag>
      <el-tag
        v-if="local.campaignStatus?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('campaignStatus')"
      >
        {{ formatTagText("状态", local.campaignStatus, campaignStatuses) }}
      </el-tag>
      <el-tag
        v-if="local.serviceStatus?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('serviceStatus')"
      >
        {{ formatTagText("服务状态", local.serviceStatus, serviceStatuses) }}
      </el-tag>
      <el-tag
        v-if="local.tags?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('tags')"
      >
        {{ formatTagText("活动标签", local.tags, tagsList) }}
      </el-tag>
      <el-tag
        v-if="local.owners?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('owners')"
      >
        {{ formatTagText("负责人", local.owners, owners) }}
      </el-tag>

      <el-tag
        v-if="local.biddingType"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('biddingType')"
      >
        竞价策略：{{ biddingTypeLabel[local.biddingType] || local.biddingType }}
      </el-tag>
      <el-tag
        v-if="local.campaignName"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('campaignName')"
      >
        广告活动：{{ local.campaignName }}
      </el-tag>

      <el-icon class="clear-all-icon" title="清空所有" @click="onReset"><Brush /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { PropType } from "vue";
import { Filter, Search, Brush, Close } from "@element-plus/icons-vue";
import FsSelect from "@/components/FsSelect.vue";

const props = defineProps({
  filters: { type: Object as () => any, required: true },
  countries: { type: Array as () => any[], default: () => [] },
  profiles: { type: Array as () => any[], default: () => [] },
  adsTypes: { type: Array as () => any[], default: () => [] },
  portfolios: { type: Array as () => any[], default: () => [] },
  skuOptions: { type: Array as () => any[], default: () => [] },
  tagsList: { type: Array as () => any[], default: () => [] },
  owners: { type: Array as () => any[], default: () => [] },
  campaignStatuses: { type: Array as () => any[], default: () => [] },
  serviceStatuses: { type: Array as () => any[], default: () => [] },
  biddingTypes: { type: Array as () => any[], default: () => [] },
  remoteSearchSku: { type: Object as PropType<(query: string) => void>, required: true },
  remoteSearchPortfolio: { type: Object as PropType<(query: string) => void>, required: true },
});

const emit = defineEmits(["update:filters", "search", "reset", "open-templates"]);

const initLocal = () => {
  const defaultValues = JSON.parse(JSON.stringify(props.filters));
  if (!defaultValues.range || defaultValues.range.length !== 2) {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);

    // 格式化为 YYYY-MM-DD
    const formatDate = (date: Date) => {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, "0");
      const d = String(date.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    };

    defaultValues.range = [formatDate(start), formatDate(end)];
  }
  return defaultValues;
};

const local = ref(initLocal());
let isUpdating = false;

watch(
  () => props.filters,
  (newVal) => {
    if (isUpdating) {
      isUpdating = false;
      return;
    }
    const newStr = JSON.stringify(newVal);
    const oldStr = JSON.stringify(local.value);
    if (newStr !== oldStr) {
      local.value = JSON.parse(newStr);
    }
  },
  { deep: true }
);

watch(
  local,
  (newVal) => {
    isUpdating = true;
    emit("update:filters", JSON.parse(JSON.stringify(newVal)));
  },
  { deep: true }
);

// 竞价策略 label 由后端 shop_profile_view options 接口统一返回，前端仅做展示回显
const biddingTypeLabel = computed(() => {
  const map: Record<string, string> = {};
  for (const bt of props.biddingTypes || []) {
    map[bt.value] = bt.label;
  }
  return map;
});

const getOptionLabel = (val: any, options: any[]) => {
  if (!options) return val;
  const opt = options.find((o: any) => o.value === val || o.id === val);
  return opt ? opt.label || opt.name || val : val;
};

const formatTagText = (prefix: string, values: any[], options?: any[]) => {
  if (!values || !values.length) return "";
  const labels = options ? values.map((v) => getOptionLabel(v, options)) : values;
  if (labels.length <= 2) {
    return `${prefix}: ${labels.join(", ")}`;
  } else {
    return `${prefix}: ${labels.slice(0, 2).join(", ")}等${labels.length}项`;
  }
};

const hasSelected = computed(() => {
  return (
    local.value.countries?.length > 0 ||
    local.value.profiles?.length > 0 ||
    local.value.adsTypes?.length > 0 ||
    local.value.portfolios?.length > 0 ||
    local.value.skus?.length > 0 ||
    local.value.campaignStatus?.length > 0 ||
    local.value.serviceStatus?.length > 0 ||
    local.value.tags?.length > 0 ||
    local.value.owners?.length > 0 ||
    !!local.value.biddingType
  );
});

function clearField(field: string) {
  const v = local.value[field];
  if (Array.isArray(v)) {
    local.value[field] = [];
  } else {
    local.value[field] = "";
  }
  onSearch();
}

function onSearch() {
  emit("search");
}

function onReset() {
  emit("reset");
}

function openTemplates() {
  emit("open-templates");
}
</script>

<style scoped>
.filters-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.filter-row-main {
  flex-wrap: nowrap;
}

.filter-row-secondary {
  flex-wrap: nowrap;
}

.filter-item {
  flex-shrink: 0;
  overflow: visible;
}

.w-90 {
  width: 90px;
}
.w-100 {
  width: 100px;
}
.w-110 {
  width: 110px;
}
.w-120 {
  width: 120px;
}
.w-130 {
  width: 130px;
}
.w-80 {
  width: 80px;
}
.w-160 {
  width: 160px;
}
.w-150 {
  width: 150px;
}

/* 筛选框高度 */
.filter-row :deep(.el-select__wrapper),
.filter-row :deep(.el-input__wrapper) {
  min-height: 34px;
  background: var(--surface-subtle);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-md);
  box-shadow: none;
  transition:
    background var(--transition-ui),
    border-color var(--transition-ui),
    box-shadow var(--transition-ui);
}

.filter-row :deep(.el-select__wrapper:hover),
.filter-row :deep(.el-input__wrapper:hover) {
  background: var(--surface-base);
  border-color: var(--color-primary-200);
}

.filter-row :deep(.el-select__wrapper.is-focused),
.filter-row :deep(.el-input__wrapper.is-focus) {
  background: var(--surface-base);
  border-color: var(--color-primary-600);
  box-shadow: 0 0 0 3px var(--focus-ring);
}

.filter-row :deep(.el-input__inner),
.filter-row :deep(.el-select__placeholder) {
  font-size: 13px;
  color: var(--text-primary);
}

.filter-row :deep(.el-input__inner::placeholder) {
  color: var(--text-tertiary);
}

.filter-row :deep(.el-range-editor.el-input__wrapper) {
  min-height: 34px;
  padding-top: 0;
  padding-bottom: 0;
}

.campaign-input {
  flex: 1 1 200px;
  width: 200px;
  max-width: 320px;
}

.date-picker {
  flex: 0 0 210px;
  width: 210px;
}

:deep(.date-picker .el-range-editor.el-input__wrapper),
:deep(.date-picker.el-range-editor.el-input__wrapper) {
  width: 210px !important;
  padding: 0 8px;
}

.input-group-seamless {
  display: flex;
  align-items: center;
}

.btn-msku-clear {
  padding: 5px 6px;
  color: var(--color-gray-500);
  border-left: 0;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.input-group-seamless :deep(.seamless-left .el-input__wrapper) {
  border-right: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.input-group-seamless :deep(.seamless-left .el-input__wrapper.is-focus) {
  z-index: 1;
  border-right: 1px solid var(--color-primary-500);
}

.input-group-seamless :deep(.seamless-right .el-input__wrapper) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.filter-actions {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-left: 2px;
}

.filter-actions :deep(.el-button) {
  height: 34px;
  border-radius: 10px;
}

.filter-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.btn-template {
  height: 34px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--surface-base);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
}

.btn-template:hover {
  color: var(--color-primary-600);
  background: var(--surface-hover);
  border-color: var(--color-primary-300);
}

/* 图标独立按钮 */
.btn-icon-only {
  width: 34px;
  height: 34px;
  padding: 0;
}

/* 已选标签行 */
.filter-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px 0 0;
  border-top: 1px solid var(--border-subtle);
}

.filter-tag {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  height: 26px;
  padding: 0 10px 0 12px;
  font-size: 12px;
  font-weight: 500;
  line-height: 24px;
  color: var(--color-primary-700);
  background: var(--surface-hover);
  border-color: var(--color-primary-200);
  border-radius: 999px;
  transition:
    background 160ms ease,
    border-color 160ms ease;
}

.filter-tag:hover {
  background: var(--color-primary-100);
  border-color: var(--color-primary-300);
}

.filter-tag :deep(.el-tag__close) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-top: 1px;
  font-size: 12px;
  color: var(--color-primary-400);
  border-radius: 999px;
  transition: all 160ms ease;
}

.filter-tag :deep(.el-tag__close:hover) {
  color: #ffffff;
  background-color: var(--color-primary-600);
  transform: scale(1.08);
}

.clear-all-icon {
  margin-left: 2px;
  font-size: 14px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 160ms ease;
}

.clear-all-icon:hover {
  color: var(--color-danger-600);
}

@media (max-width: 1400px) {
  .filter-row-main,
  .filter-row-secondary {
    flex-wrap: wrap;
  }
}
</style>
