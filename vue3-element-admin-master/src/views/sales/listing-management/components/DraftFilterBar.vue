<template>
  <el-form :inline="true" :model="filterParams" size="small" class="drafts-filter-form">
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
            <el-icon :size="14" class="filter-tip-icon"><InfoFilled /></el-icon>
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
      <el-input v-model="filterParams.msku" placeholder="请输入MSKU" class="filter-search-input">
        <template #append>
          <el-button type="primary" :icon="Search">搜索</el-button>
        </template>
      </el-input>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
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

function disabledDate(time: Date) {
  return time.getTime() > Date.now();
}
</script>

<style scoped lang="scss">
.drafts-filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;

  :deep(.el-form-item) {
    margin-right: 16px;
    margin-bottom: 12px;
  }
}

.filter-select--sm {
  width: 100px;
}

.filter-daterange {
  width: 200px;
}

.filter-search-input {
  width: 240px;
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
</style>
