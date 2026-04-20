<template>
  <div class="filters-container">
    <div class="filter-row">
      <FsSelect
        v-model="local.countries"
        class="filter-item w-160"
        :options="countries"
        multiple
        placeholder="选择国家"
      />
      <FsSelect
        v-model="local.profiles"
        class="filter-item w-160"
        :options="profiles"
        multiple
        placeholder="选择店铺"
      />
      <el-date-picker
        v-model="local.range"
        class="filter-item date-picker-custom"
        type="daterange"
        start-placeholder="开始"
        end-placeholder="结束"
        range-separator="-"
        value-format="YYYY-MM-DD"
        unlink-panels
      />
      <FsSelect
        v-model="local.adsTypes"
        class="filter-item w-140"
        :options="adsTypes"
        multiple
        placeholder="全部广告类型"
      />
      <FsSelect
        v-model="local.targetTypes"
        class="filter-item w-140"
        :options="targetTypes"
        multiple
        placeholder="全部投放类型"
      />
      <FsSelect
        v-model="local.portfolios"
        class="filter-item w-140"
        :options="portfolios"
        multiple
        placeholder="广告组合"
      />
    </div>

    <div class="filter-row">
      <div class="filter-item input-group-seamless">
        <el-select
          v-model="local.asinSearchType"
          class="seamless-left w-120"
          placeholder="ASIN查询"
        >
          <el-option label="按ASIN/MSKU查询" value="sku" />
          <el-option label="按父ASIN查询" value="parent_asin" />
        </el-select>
        <FsSelect
          v-model="local.skus"
          :options="skuOptions"
          multiple
          remote
          :remote-method="remoteSearchSku"
          placeholder="全部MSKU"
          :show-only="true"
          class="seamless-right w-160"
        />
      </div>
      <FsSelect
        v-model="local.campaignStatus"
        class="filter-item w-120"
        :options="campaignStatuses"
        multiple
        placeholder="全部状态"
      />
      <FsSelect
        v-model="local.serviceStatus"
        class="filter-item w-140"
        :options="serviceStatuses"
        multiple
        placeholder="全部服务状态"
      />
      <el-select
        v-model="local.budgetType"
        class="filter-item w-120"
        placeholder="预算类型"
        clearable
      >
        <el-option label="每日预算" value="daily" />
        <el-option label="终生预算" value="lifetime" />
      </el-select>
      <el-select
        v-model="local.biddingType"
        class="filter-item w-120"
        placeholder="竞价策略"
        clearable
      >
        <el-option label="动态竞价-只降低" value="legacyForSales" />
        <el-option label="动态竞价-提高和降低" value="autoForSales" />
        <el-option label="固定竞价" value="manual" />
        <el-option label="基于规则的竞价" value="ruleBased" />
      </el-select>
      <el-select
        v-model="local.costType"
        class="filter-item w-120"
        placeholder="成本类型"
        clearable
      >
        <el-option label="CPC" value="cpc" />
        <el-option label="VCPM" value="vcpm" />
      </el-select>
      <el-select
        v-model="local.siteRestrictions"
        class="filter-item w-120"
        placeholder="网站"
        clearable
      >
        <el-option label="亚马逊站内外" value="AMAZON_ALL" />
        <el-option label="亚马逊企业购" value="AMAZON_BUSINESS" />
      </el-select>
      <el-select
        v-model="local.adsStrategy"
        class="filter-item w-120"
        placeholder="广告工具"
        clearable
      >
        <el-option label="分时策略" value="TimingTactics" />
        <el-option label="递增预算" value="StepBudget" />
        <el-option label="自动规则" value="RuleEngine" />
        <el-option label="自定义设置" value="TimingCustomSet" />
        <el-option label="未使用工具" value="NotAppliedTool" />
      </el-select>
    </div>

    <div class="filter-row">
      <FsSelect
        v-model="local.tags"
        class="filter-item w-140"
        :options="tagsList"
        multiple
        placeholder="活动标签"
      />
      <FsSelect
        v-model="local.owners"
        class="filter-item w-140"
        :options="owners"
        multiple
        placeholder="负责人"
      />

      <el-input
        v-model="local.campaignName"
        class="filter-item w-280"
        placeholder="Y-PX-SY01 露肩V领修身上衣 酒红/黑"
        clearable
      >
        <template #suffix>
          <el-icon><Operation /></el-icon>
        </template>
      </el-input>

      <div class="filter-actions">
        <el-button class="btn-template" @click="openTemplates">
          <el-icon style="margin-right: 4px"><Filter /></el-icon>
          筛选模板
        </el-button>
        <el-button type="primary" class="btn-search" @click="onSearch">查询</el-button>
        <el-button class="btn-reset" @click="onReset">重置</el-button>
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
        v-if="local.targetTypes?.length"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('targetTypes')"
      >
        {{ formatTagText("投放类型", local.targetTypes, targetTypes) }}
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
        v-if="local.budgetType"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('budgetType')"
      >
        预算类型：{{ dicts.budgetType[local.budgetType] }}
      </el-tag>
      <el-tag
        v-if="local.biddingType"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('biddingType')"
      >
        竞价策略：{{ dicts.biddingType[local.biddingType] }}
      </el-tag>
      <el-tag
        v-if="local.costType"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('costType')"
      >
        成本类型：{{ dicts.costType[local.costType] }}
      </el-tag>
      <el-tag
        v-if="local.siteRestrictions"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('siteRestrictions')"
      >
        网站：{{ dicts.siteRestrictions[local.siteRestrictions] }}
      </el-tag>
      <el-tag
        v-if="local.adsStrategy"
        closable
        effect="plain"
        class="filter-tag"
        @close="clearField('adsStrategy')"
      >
        广告工具：{{ dicts.adsStrategy[local.adsStrategy] }}
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

      <el-icon class="clear-all-icon" title="清空所有" @click="onReset"><Delete /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { PropType } from "vue";
import { Filter, Operation, Delete } from "@element-plus/icons-vue";
import FsSelect from "@/components/FsSelect.vue";

const props = defineProps({
  filters: { type: Object as () => any, required: true },
  countries: { type: Array as () => any[], default: () => [] },
  profiles: { type: Array as () => any[], default: () => [] },
  adsTypes: { type: Array as () => any[], default: () => [] },
  targetTypes: { type: Array as () => any[], default: () => [] },
  portfolios: { type: Array as () => any[], default: () => [] },
  skuOptions: { type: Array as () => any[], default: () => [] },
  tagsList: { type: Array as () => any[], default: () => [] },
  owners: { type: Array as () => any[], default: () => [] },
  campaignStatuses: { type: Array as () => any[], default: () => [] },
  serviceStatuses: { type: Array as () => any[], default: () => [] },
  remoteSearchSku: { type: Object as PropType<(query: string) => void>, required: true },
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

const dicts: Record<string, Record<string, string>> = {
  budgetType: { daily: "每日预算", lifetime: "终生预算" },
  biddingType: {
    legacyForSales: "动态竞价-只降低",
    autoForSales: "动态竞价-提高和降低",
    manual: "固定竞价",
    ruleBased: "基于规则的竞价",
  },
  costType: { cpc: "CPC", vcpm: "VCPM" },
  siteRestrictions: { AMAZON_ALL: "亚马逊站内外", AMAZON_BUSINESS: "亚马逊企业购" },
  adsStrategy: {
    TimingTactics: "分时策略",
    StepBudget: "递增预算",
    RuleEngine: "自动规则",
    TimingCustomSet: "自定义设置",
    NotAppliedTool: "未使用工具",
  },
};

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
    local.value.targetTypes?.length > 0 ||
    local.value.portfolios?.length > 0 ||
    local.value.skus?.length > 0 ||
    local.value.campaignStatus?.length > 0 ||
    local.value.serviceStatus?.length > 0 ||
    local.value.tags?.length > 0 ||
    local.value.owners?.length > 0 ||
    local.value.budgetType ||
    local.value.biddingType ||
    local.value.costType ||
    local.value.siteRestrictions ||
    local.value.adsStrategy ||
    local.value.campaignName
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
  gap: 8px;
  align-items: center;
}
.filter-item {
  flex-shrink: 0;
}
.w-120 {
  width: 120px;
}
.w-140 {
  width: 140px;
}
.w-160 {
  width: 160px;
}
.w-200 {
  width: 200px !important;
}
.w-240 {
  width: 240px;
}
.w-280 {
  width: 280px;
}
.w-300 {
  width: 300px !important;
}

.date-picker-custom {
  width: 240px !important;
  --el-date-editor-width: 240px !important;
  min-width: 240px !important;
  max-width: 240px !important;
}

:deep(.el-range-editor.el-input__wrapper) {
  padding: 0 8px;
}

.input-group-seamless {
  display: flex;
  align-items: center;
}
.input-group-seamless :deep(.seamless-left .el-input__wrapper) {
  border-right: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}
.input-group-seamless :deep(.seamless-left .el-input__wrapper.is-focus) {
  z-index: 1;
  border-right: 1px solid var(--el-color-primary);
}
.input-group-seamless :deep(.seamless-right .el-input__wrapper) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: 4px;
}
.btn-template {
  color: #606266;
}
.btn-search {
  min-width: 60px;
}
.btn-reset {
  min-width: 60px;
}

.filter-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
}
.filter-tag {
  height: 28px;
  padding: 0 10px;
  font-size: 13px;
  line-height: 26px;
  color: #409eff;
  background: #fdfdfd;
  border-color: #a0cfff;
  border-radius: 4px;
}
.filter-tag :deep(.el-tag__close) {
  color: #a0cfff;
}
.filter-tag :deep(.el-tag__close:hover) {
  color: #fff;
  background-color: #409eff;
}
.clear-all-icon {
  margin-left: 2px;
  font-size: 16px;
  color: #606266;
  cursor: pointer;
}
.clear-all-icon:hover {
  color: #f56c6c;
}
</style>
