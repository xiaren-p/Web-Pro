<template>
  <div class="page-container app-container">
    <LossOrderSearchForm
      :filters="filters"
      :shops="shops"
      :owners="owners"
      :date-shortcuts="dateShortcuts"
      @query="handleQuery"
      @reset="handleReset"
    />

    <LossOrderTable
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      :syncing="syncing"
      :sync-time-display="syncTimeDisplay"
      @sort-change="handleSortChange"
      @page-change="onPageChange"
      @size-change="onPageSizeChange"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 亏损订单统计页（瘦页面）：
 * 仅做"组装"工作 —— 拉店铺/负责人下拉、托管 filters 模型、把数据生命周期交给
 * `useLossOrderQuery`，把表单与表格渲染交给两个子组件。
 * 所属板块：statistics / lossmakingOrders。
 */
import { reactive, ref, onMounted } from "vue";

import { fetchShopOptions, fetchListingOwnerOptions } from "@/api/lossmakingOrders";
import { createDateShortcuts } from "@/composables/lossmakingOrders/useDateShortcuts";
import {
  useLossOrderQuery,
  type LossOrderFilters,
} from "@/composables/lossmakingOrders/useLossOrderQuery";

import LossOrderSearchForm from "./components/LossOrderSearchForm.vue";
import LossOrderTable from "./components/LossOrderTable.vue";

defineOptions({ name: "LossmakingOrders" });

// 默认下单时间：最近 7 天（含今天）
const defaultEndDate = new Date();
const defaultStartDate = new Date();
defaultStartDate.setDate(defaultEndDate.getDate() - 6);

const filters = reactive<LossOrderFilters>({
  shops: [],
  currency: "EUR",
  owners: [],
  // el-date-picker 同时接受 string[] / Date[]，运行期保留 Date 对象
  orderDateRange: [defaultStartDate, defaultEndDate] as any,
  msku: "",
  rule: "rule1",
});

const shops = ref<Array<{ label: string; value: string; country?: string }>>([]);
const owners = ref<Array<{ label: string; value: string }>>([]);

const dateShortcuts = createDateShortcuts((range) => {
  filters.orderDateRange = range;
});

const {
  loading,
  tableData,
  pagination,
  syncing,
  syncTimeDisplay,
  handleQuery,
  handleSortChange,
  onPageChange,
  onPageSizeChange,
} = useLossOrderQuery(filters, shops);

/** 重置筛选模型并重新查询。 */
function handleReset() {
  filters.msku = "";
  filters.orderDateRange = [];
  filters.shops = [];
  filters.currency = "EUR";
  filters.owners = [];
  filters.rule = "rule1";
  handleQuery();
}

onMounted(async () => {
  try {
    const s = await fetchShopOptions();
    shops.value = (s || []).map((x: any) => ({
      label: x.name || x.label || x.shop,
      value: x.id || x.value || x.shop,
      country: x.country,
    }));
  } catch (e) {
    console.error("获取店铺失败", e);
  }

  try {
    const o = await fetchListingOwnerOptions();
    owners.value = (o || []).map((x: any) => ({
      label: x.name || x.label,
      value: x.id || x.value,
    }));
  } catch (e) {
    console.error("获取负责人失败", e);
  }

  await handleQuery();
});
</script>

<style scoped lang="scss">
.page-container {
  padding: 16px;
}
</style>
