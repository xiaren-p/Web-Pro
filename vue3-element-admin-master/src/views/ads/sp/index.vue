<template>
  <div class="ads-text-container">
    <section class="content-block filter-panel-block">
      <Filters
        :filters="filters"
        :countries="countries"
        :profiles="filteredProfiles"
        :portfolios="portfolios"
        :sku-options="skuOptions"
        :tags-list="tagsList"
        :owners="owners"
        :campaign-statuses="campaignStatuses"
        :service-statuses="serviceStatuses"
        :bidding-types="biddingTypes"
        :remote-search-sku="remoteSearchSku"
        :remote-search-portfolio="remoteSearchPortfolio"
        @update:filters="(v) => Object.assign(filters, v)"
        @search="search"
        @reset="resetFilters"
        @open-templates="openSearchTemplates"
      />
    </section>

    <section class="content-block indicators-panel-block">
      <Indicators :summary="summary" />
    </section>

    <section class="content-block data-table-block">
      <div class="table-controls">
        <div class="left-controls">
          <div class="table-controls__title-group">
            <h2 class="table-controls__title">广告活动列表</h2>
            <span class="table-controls__summary">{{ tableColumns.length }} 个显示字段</span>
          </div>
          <el-dropdown @command="handleNewAdCommand">
            <el-button type="primary" class="primary-action-button">
              新建广告
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="upload">文件上传</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button class="queue-action-button" @click="queueDrawerVisible = true">
            查看队列
          </el-button>
        </div>

        <div class="right-controls">
          <el-checkbox v-model="onlyOverBudget" class="risk-switch">只查看超预算</el-checkbox>
          <el-tooltip content="列配置" placement="top">
            <el-button class="column-config-btn" @click="restoreDefaultColumns">
              <el-icon><Operation /></el-icon>
              列配置
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <AdsTable
        :loading="loading"
        :table-data="tableData"
        :page-size="pageSize"
        :current-page="currentPage"
        :total="total"
        :columns="tableColumns"
        :summary="summary"
        :date-range="filters.range"
        @current-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        @sort-change="handleSortChange"
      />
    </section>

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />

    <!-- 广告上传队列抽屉 -->
    <AdQueueDrawer v-model:visible="queueDrawerVisible" />
    <!-- 新建广告上传对话框 -->
    <AdUploadDialog v-model:visible="uploadDialogVisible" @view-queue="queueDrawerVisible = true" />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from "vue";
import { ArrowDown, Operation } from "@element-plus/icons-vue";
import Filters from "./Filters.vue";
import Indicators from "./Indicators.vue";
import AdsTable from "./AdsTable.vue";
import AdQueueDrawer from "./AdQueueDrawer.vue";
import AdUploadDialog from "./AdUploadDialog.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { ElMessage } from "element-plus";
import {
  getAdCampaigns,
  getAdEnumLabels,
  getAdOptions,
  getAdPortfolioOptions,
  getAdSkuOptions,
} from "@/api/ads";
import { ShopsAPI } from "@/api/shops";

defineOptions({ name: "AdsText" });

// ── 广告上传队列 ──────────────────────────────────────────────────────────────
const queueDrawerVisible = ref(false);
const uploadDialogVisible = ref(false);
/**
 * 处理"新建广告"下拉命令：打开上传对话框。
 *
 * @param {string} command - 下拉项命令值，当前仅支持 "upload"
 */
function handleNewAdCommand(command: string): void {
  if (command === "upload") {
    uploadDialogVisible.value = true;
  }
}

// ── 广告列表 ──────────────────────────────────────────────────────────────────
const onlyOverBudget = ref(false);

// 切换超预算筛选时自动刷新表格
watch(onlyOverBudget, () => {
  currentPage.value = 1;
  loadTableData();
});

const countries = ref<{ value: string; label: string }[]>([]);
const profiles = ref<{ value: string; label: string; country?: string }[]>([]);
const portfolios = ref<{ value: string; label: string }[]>([]);
const biddingTypes = ref<{ value: string; label: string }[]>([]);
const owners = ref<{ value: string; label: string }[]>([]);
const summary = ref<Record<string, unknown> | null>(null);

onMounted(() => {
  getAdOptions().then((res: any) => {
    countries.value = res.countries || [];
    profiles.value = res.profiles || [];
    biddingTypes.value = res.bidding_types || [];
  });

  remoteSearchPortfolio("");
  loadOwners();
  loadSkuOptions();
  loadAllEnumLabels();
});

const tagsList = ref<any[]>([]);

const campaignStatuses = ref<any[]>([]);
const serviceStatuses = ref<any[]>([]);

async function loadEnumLabels(module: string): Promise<any[]> {
  try {
    const res = await getAdEnumLabels({ module });
    return res.labels || [];
  } catch (error) {
    console.error(`加载枚举 ${module} 失败`, error);
    return [];
  }
}

async function loadAllEnumLabels(): Promise<void> {
  const [campaignLabels, serviceLabels, tagLabels] = await Promise.all([
    loadEnumLabels("campaign_status"),
    loadEnumLabels("service_status"),
    loadEnumLabels("tags"),
  ]);
  campaignStatuses.value = campaignLabels;
  serviceStatuses.value = serviceLabels;
  tagsList.value = tagLabels;
}

const allSkus = ref<any[]>([]);
const skuOptions = ref<any[]>([]);

async function loadSkuOptions(): Promise<void> {
  try {
    const res = await getAdSkuOptions({});
    allSkus.value = res.skus || [];
    syncSkuOptions("");
  } catch (error) {
    console.error("加载 SKU 下拉失败", error);
  }
}

function buildParentAsinOptions(options: any[]): any[] {
  return options
    .filter((item: any) => {
      const code = String(item.code || "");
      const parentAsin = String(item.parent || item.parent_asin || "");
      return code && parentAsin && code === parentAsin;
    })
    .map((item: any) => {
      const parentAsin = String(item.parent || item.parent_asin || item.code);
      return {
        ...item,
        value: parentAsin,
        label: parentAsin,
        code: parentAsin,
      };
    });
}

function syncSkuOptions(query: string): void {
  const q = query.toLowerCase();
  const sourceOptions =
    filters.asinSearchType === "parent_asin"
      ? buildParentAsinOptions(allSkus.value)
      : allSkus.value;
  if (!q) {
    skuOptions.value = sourceOptions.slice();
    return;
  }
  skuOptions.value = sourceOptions.filter((s: any) =>
    `${s.title || ""}${s.code || ""}${s.value || ""}`.toLowerCase().includes(q)
  );
}

function remoteSearchSku(query: string) {
  syncSkuOptions(query);
}

const filters = reactive({
  countries: [] as string[],
  profiles: [] as string[],
  range: [] as string[],
  adsTypes: [] as string[],
  portfolios: [] as string[],
  asinSearchType: "sku",
  skus: [] as string[],
  biddingType: "",
  tags: [] as string[],
  owners: [] as string[],
  campaignName: "",
  campaignStatus: [] as string[],
  serviceStatus: [] as string[],
});

watch(
  () => filters.asinSearchType,
  () => {
    filters.skus = [];
    syncSkuOptions("");
  }
);

/**
 * 国家变更时联动清空不匹配的店铺。
 */
watch(
  () => filters.countries,
  (newCountries) => {
    if (!filters.profiles || filters.profiles.length === 0) return;
    if (newCountries.length === 0) return;
    const countrySet = new Set(newCountries);
    const validProfiles = filters.profiles.filter((pid: string) => {
      const profile = profiles.value.find((p) => p.value === pid);
      return profile ? countrySet.has(profile.country ?? "") : true;
    });
    if (validProfiles.length !== filters.profiles.length) {
      filters.profiles = validProfiles;
    }
  }
);

const columnConfigVisible = ref(false);

/**
 * 根据已选国家过滤店铺列表：未选国家时展示全部，选择国家后仅展示匹配的店铺。
 */
const filteredProfiles = computed(() => {
  if (!filters.countries || filters.countries.length === 0) return profiles.value;
  const selectedSet = new Set(filters.countries);
  return profiles.value.filter((p) => selectedSet.has(p.country ?? ""));
});

const defaultColumns = [
  // 设置
  { label: "服务状态", prop: "service_status", visible: true, category: "设置", sortable: false },
  { label: "竞价策略", prop: "bidding_type", visible: true, category: "设置", sortable: false },
  { label: "广告组合", prop: "portfolio_name", visible: true, category: "设置", sortable: false },
  { label: "预算", prop: "budget", visible: true, category: "设置", sortable: true },
  {
    label: "开始日期",
    prop: "startDate",
    visible: true,
    category: "设置",
    sortable: true,
  },
  { label: "标签", prop: "tags", visible: true, category: "设置", sortable: false },
  // 转化
  { label: "IS", prop: "is", visible: true, category: "转化", sortable: true },
  { label: "广告销售额", prop: "adsSales", visible: true, category: "转化", sortable: true },
  {
    label: "广告销售额%",
    prop: "adsSalesPercent",
    visible: true,
    category: "转化",
    sortable: true,
  },
  { label: "直接销售额", prop: "directSales", visible: true, category: "转化", sortable: true },
  { label: "广告订单", prop: "adsOrders", visible: true, category: "转化", sortable: true },
  { label: "直接订单", prop: "directOrders", visible: true, category: "转化", sortable: true },
  { label: "ACoS", prop: "acos", visible: true, category: "转化", sortable: true },
  { label: "ROAS", prop: "roas", visible: true, category: "转化", sortable: true },
  { label: "CVR", prop: "cvr", visible: true, category: "转化", sortable: true },
  {
    label: "广告笔单价",
    prop: "adsOrderPrice",
    visible: true,
    category: "转化",
    sortable: true,
  },
  { label: "广告销量", prop: "adsVolume", visible: true, category: "转化", sortable: true },
  // 业绩
  { label: "曝光量", prop: "impressions", visible: true, category: "业绩", sortable: true },
  { label: "曝光%", prop: "impressionsPercent", visible: true, category: "业绩", sortable: true },
  { label: "点击", prop: "clicks", visible: true, category: "业绩", sortable: true },
  { label: "点击%", prop: "clicksPercent", visible: true, category: "业绩", sortable: true },
  { label: "CTR", prop: "ctr", visible: true, category: "业绩", sortable: true },
  { label: "CPC", prop: "cpc", visible: true, category: "业绩", sortable: true },
  { label: "花费", prop: "spends", visible: true, category: "业绩", sortable: true },
  { label: "花费%", prop: "spendsPercent", visible: true, category: "业绩", sortable: true },
  { label: "CPA", prop: "cpa", visible: true, category: "业绩", sortable: true },
];

const activeColumns = ref(defaultColumns);
const tableColumns = computed(() => activeColumns.value.filter((col) => col.visible));

function restoreDefaultColumns() {
  columnConfigVisible.value = true;
}

function onColumnConfigSave(columns: any[]) {
  activeColumns.value = columns;
  ElMessage.success("列配置已保存");
}

function remoteSearchPortfolio(query: string = "") {
  getAdPortfolioOptions({ keyword: query }).then((res: any) => {
    portfolios.value = [{ value: "-1", label: "未设置广告组合" }, ...(res.portfolios || [])];
  });
}

async function loadOwners(): Promise<void> {
  const data = await ShopsAPI.getOwners();
  owners.value = (data || []).map((item) => ({
    value: String(item.value || item.id),
    label: item.label || item.name || String(item.value || item.id),
  }));
}

function search() {
  currentPage.value = 1;
  loadTableData();
}

function resetFilters() {
  filters.countries = [];
  filters.profiles = [];
  filters.range = [];
  filters.adsTypes = [];
  filters.portfolios = [];
  filters.asinSearchType = "sku";
  filters.skus = [];
  filters.biddingType = "";
  filters.tags = [];
  filters.owners = [];
  filters.campaignName = "";
  filters.campaignStatus = [];
  filters.serviceStatus = [];
  currentPage.value = 1;
  loadTableData();
}

const tableData = ref([] as any[]);
const total = ref(0);
const pageSize = ref(25);
const currentPage = ref(1);

const loading = ref(false);
const sortParams = reactive({
  prop: "",
  order: "",
});

async function loadTableData() {
  loading.value = true;
  try {
    const params: any = {
      pageNum: currentPage.value,
      pageSize: pageSize.value,
      name: filters.campaignName,
      state: filters.campaignStatus.join(","),
      service_status: filters.serviceStatus.join(","),
      // 勾选“只查看超预算的”时，追加超预算状态到筛选条件中
      ...(onlyOverBudget.value
        ? {
            service_status: filters.serviceStatus.length
              ? `${filters.serviceStatus.join(",")},CAMPAIGN_OUT_OF_BUDGET`
              : "CAMPAIGN_OUT_OF_BUDGET",
          }
        : {}),
      sponsored_type: filters.adsTypes.join(","),
      portfolio_id: filters.portfolios.join(","),
      bidding_type: filters.biddingType,
      tags: filters.tags.join(","),
      owners: filters.owners.join(","),
      profiles: filters.profiles.join(","),
      countries: filters.countries.join(","),
      date_start: filters.range?.[0] || "",
      date_end: filters.range?.[1] || "",
    };

    if (sortParams.prop && sortParams.order) {
      params.sort_prop = sortParams.prop;
      params.sort_order = sortParams.order === "ascending" ? "asc" : "desc";
    }

    // 如果有组合或者其他可以在这里继续加

    const res = await getAdCampaigns(params);

    // 直接使用后端纯净的真实字段！前端列配置已对齐
    tableData.value = res.list || [];
    total.value = res.total || 0;
    summary.value = res.summary ?? null;
  } catch (error) {
    console.error(error);
    ElMessage.error("获取广告列表数据失败");
  } finally {
    loading.value = false;
  }
}

function handlePageChange(page: number) {
  currentPage.value = page;
  loadTableData();
}
function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
  loadTableData();
}

function handleSortChange({ prop, order }: { prop: string; order: string }) {
  sortParams.prop = prop || "";
  sortParams.order = order || "";
  currentPage.value = 1;
  loadTableData();
}

function openSearchTemplates() {
  ElMessage.info("打开筛选模板（占位）");
}

loadTableData();
</script>

<style scoped src="./ads.scss" lang="scss"></style>
