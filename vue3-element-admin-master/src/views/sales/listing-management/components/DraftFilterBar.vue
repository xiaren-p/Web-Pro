<template>
  <section class="draft-filter-bar">
    <el-form :inline="true" :model="filterParams" size="small" class="draft-filter-bar__form">
      <el-form-item label="全部国家" prop="country">
        <el-select
          v-model="filterParams.country"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item label="全部店铺" prop="shop">
        <el-select
          v-model="filterParams.shop"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item label="草稿版本" prop="draftVersion">
        <el-select
          v-model="filterParams.draftVersion"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item label="销售类型" prop="saleType">
        <el-select
          v-model="filterParams.saleType"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item prop="requiredComplete">
        <template #label>
          <span class="filter-label-with-tip">
            必填项完整
            <el-tooltip content="是否所有必填字段已填写" placement="top">
              <el-icon :size="14" class="filter-tip-icon">
                <InfoFilled />
              </el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-select
          v-model="filterParams.requiredComplete"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item label="操作人" prop="operator">
        <el-select
          v-model="filterParams.operator"
          placeholder="全部"
          clearable
          class="filter-select filter-select--sm"
        />
      </el-form-item>

      <el-form-item label="操作时间" prop="dateRange">
        <el-date-picker
          v-model="filterParams.dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="开始日期"
          end-placeholder="截止日期"
          value-format="YYYY-MM-DD"
          :disabled-date="disabledDate"
          class="filter-daterange"
        />
      </el-form-item>

      <el-form-item label="MSKU" prop="msku">
        <el-input
          v-model="filterParams.msku"
          placeholder="请输入MSKU"
          class="filter-search-input"
          @keyup.enter="() => {}"
        >
          <template #append>
            <el-button type="primary" :icon="Search" class="filter-search-btn">搜索</el-button>
          </template>
        </el-input>
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
/**
 * 草稿箱筛选区域：8 个筛选控件（6×el-select、1×el-date-picker、1×el-input+搜索）。
 * 当前为 UI 占位，选项均为空，后续补齐后端数据源。
 */
import { reactive } from "vue";
import { Search, InfoFilled } from "@element-plus/icons-vue";

interface FilterParams {
  country: string;
  shop: string;
  draftVersion: string;
  saleType: string;
  requiredComplete: string;
  operator: string;
  dateRange: [string, string] | null;
  msku: string;
}

defineOptions({ name: "DraftFilterBar" });

const filterParams = reactive<FilterParams>({
  country: "",
  shop: "",
  draftVersion: "",
  saleType: "",
  requiredComplete: "",
  operator: "",
  dateRange: ["2026-05-31", "2026-06-30"],
  msku: "",
});

/** 禁用未来日期 */
function disabledDate(time: Date) {
  return time.getTime() > Date.now();
}
</script>

<style scoped lang="scss">
.draft-filter-bar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  height: 56px;
  padding: 0 var(--spacing-4);
  background: var(--surface-subtle);

  &__form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;

    :deep(.el-form-item) {
      margin-right: var(--spacing-3);
      margin-bottom: 0;

      &:last-child {
        margin-right: 0;
      }
    }

    :deep(.el-form-item__label) {
      height: 32px;
      padding-right: var(--spacing-1);
      font-size: var(--font-size-sm);
      line-height: 32px;
      color: var(--text-primary);
    }
  }
}

.filter-select {
  &--sm {
    width: 100px;

    :deep(.el-select__wrapper) {
      min-height: 32px;
      border-radius: var(--radius-sm);
    }
  }
}

.filter-daterange {
  width: 200px;

  :deep(.el-input__wrapper) {
    min-height: 32px;
    border-radius: var(--radius-sm);
  }
}

.filter-search-input {
  width: 240px;

  :deep(.el-input__wrapper) {
    min-height: 32px;
    border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  }

  :deep(.el-input-group__append) {
    padding: 0;
  }
}

.filter-search-btn {
  height: 32px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.filter-label-with-tip {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.filter-tip-icon {
  color: var(--text-tertiary);
  cursor: help;
}

/* 响应式：≤768px 筛选区换行 */
@media (width <= 768px) {
  .draft-filter-bar {
    height: auto;
    padding: var(--spacing-2) var(--spacing-4);
  }
}
</style>
