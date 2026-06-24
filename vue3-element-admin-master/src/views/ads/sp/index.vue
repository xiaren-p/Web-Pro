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
        @update-budget="onUpdateBudget"
        @update-state="onUpdateState"
        @batch-state="onBatchState"
        @batch-budget="onBatchBudgetOpen"
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
    <!-- 批量调整预算对话框 -->
    <BatchBudgetDialog
      v-model="batchBudgetDialogVisible"
      :items="batchBudgetItems"
      :currency-icon="batchBudgetCurrencyIcon"
      @confirm="onBatchBudgetConfirm"
    />
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
import BatchBudgetDialog from "@/components/BatchBudgetDialog/index.vue";
import type { BatchBudgetItem } from "@/components/BatchBudgetDialog/index.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { ElMessage } from "element-plus";
import {
  getAdCampaigns,
  getAdEnumLabels,
  getAdOptions,
  getAdPortfolioOptions,
  getAdSkuOptions,
} from "@/api/ads";
import {
  createCampaignStateAdjustment,
  createManualBudgetAdjustment,
  batchAdjustCampaignState,
  batchAdjustCampaignBudget,
} from "@/api/ads/campaign-adjustment";
import { ShopsAPI } from "@/api/shops";

defineOptions({ name: "AdsText" });

// ── 浏览器缓存：记忆用户筛选 / 分页 / 列配置等手动选择 ──────────────────────────
const STORAGE_KEYS = {
  filters: "ADS_SP_FILTERS_V1",
  pagination: "ADS_SP_PAGINATION_V1",
  columns: "ADS_SP_COLUMNS_V1",
  overBudget: "ADS_SP_OVERBUDGET_V1",
  sort: "ADS_SP_SORT_V1",
} as const;

/**
 * 安全读取 localStorage JSON 缓存。
 *
 * @param {string} key - 缓存键
 * @returns {unknown|null} 解析后的值；读取失败或不存在返回 null
 */
function readCache(key: string): unknown {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * 安全写入 localStorage JSON 缓存。
 *
 * @param {string} key - 缓存键
 * @param {unknown} value - 待序列化写入的值
 */
function writeCache(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 容量满或隐私模式：静默忽略，不影响业务
  }
}

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
const onlyOverBudget = ref<boolean>(
  (() => {
    const cached = readCache(STORAGE_KEYS.overBudget);
    return typeof cached === "boolean" ? cached : false;
  })()
);

// 切换超预算筛选时自动刷新表格并持久化
watch(onlyOverBudget, (v) => {
  writeCache(STORAGE_KEYS.overBudget, v);
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

/**
 * 从 localStorage 恢复筛选状态；无缓存时返回全空默认值。
 * range 留空，由 Filters.vue 在无缓存时回填 7 天默认值。
 */
function initFiltersFromCache(): Record<string, unknown> {
  const cached = readCache(STORAGE_KEYS.filters);
  const defaults = {
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
  };
  if (cached && typeof cached === "object") {
    // 仅取已知字段，避免脏数据注入；数组类型校验
    const c = cached as Record<string, unknown>;
    const merged: Record<string, unknown> = { ...defaults };
    for (const k of Object.keys(defaults)) {
      const v = c[k];
      if (Array.isArray(defaults[k as keyof typeof defaults])) {
        if (Array.isArray(v)) merged[k] = v;
      } else if (typeof v === "string") {
        merged[k] = v;
      }
    }
    return merged;
  }
  return defaults;
}

const filters = reactive(
  initFiltersFromCache() as {
    countries: string[];
    profiles: string[];
    range: string[];
    adsTypes: string[];
    portfolios: string[];
    asinSearchType: string;
    skus: string[];
    biddingType: string;
    tags: string[];
    owners: string[];
    campaignName: string;
    campaignStatus: string[];
    serviceStatus: string[];
  }
);

// 筛选变更时持久化（deep watch，与 Filters.vue 的 emit 同步触发）
watch(
  filters,
  (v) => {
    writeCache(STORAGE_KEYS.filters, { ...v });
  },
  { deep: true }
);

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

/**
 * 初始化列配置：合并本地缓存与默认配置。
 * 缓存列按其顺序保留 visible/fixed，默认列补齐 label/category 与新增列。
 */
function initColumns(): any[] {
  const cached = readCache(STORAGE_KEYS.columns);
  if (cached && Array.isArray(cached)) {
    try {
      const defaultMap = new Map(defaultColumns.map((c) => [c.prop, c]));
      const cachedProps = new Set<string>();
      const merged = cached
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
    } catch {
      // 缓存损坏：回退默认
    }
  }
  return JSON.parse(JSON.stringify(defaultColumns));
}

const activeColumns = ref(initColumns());
const tableColumns = computed(() => activeColumns.value.filter((col) => col.visible));

function restoreDefaultColumns() {
  columnConfigVisible.value = true;
}

function onColumnConfigSave(columns: any[]) {
  activeColumns.value = columns;
  writeCache(STORAGE_KEYS.columns, columns);
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
// 分页从缓存恢复（pageSize / currentPage）
const _cachedPagination = readCache(STORAGE_KEYS.pagination) as {
  pageSize?: number;
  currentPage?: number;
} | null;
const pageSize = ref<number>(
  _cachedPagination?.pageSize && _cachedPagination.pageSize > 0 ? _cachedPagination.pageSize : 25
);
const currentPage = ref<number>(
  _cachedPagination?.currentPage && _cachedPagination.currentPage > 0
    ? _cachedPagination.currentPage
    : 1
);

const loading = ref(false);
// 排序从缓存恢复
const _cachedSort = readCache(STORAGE_KEYS.sort) as { prop?: string; order?: string } | null;
const sortParams = reactive({
  prop: _cachedSort?.prop || "",
  order: _cachedSort?.order || "",
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

    // 持久化当前分页位置（加载成功后写回，避免失败状态被记忆）
    writeCache(STORAGE_KEYS.pagination, {
      pageSize: pageSize.value,
      currentPage: currentPage.value,
    });
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
  writeCache(STORAGE_KEYS.sort, { prop: sortParams.prop, order: sortParams.order });
  currentPage.value = 1;
  loadTableData();
}

function openSearchTemplates() {
  ElMessage.info("打开筛选模板（占位）");
}

// ── 手动调整预算 / 状态（写调整记录表 + 更新本地实体，不触发亚马逊推送）──────────

/**
 * 处理预算修改：调用后端 adjust-budget 接口，成功后更新行内 budget 字段。
 * 失败时由 AdsTable 还原编辑框值（通过 row.budget 未被修改实现）。
 *
 * @param {Object} payload - { row, budget }
 * @param {any} payload.row - 表格行数据
 * @param {number} payload.budget - 新预算值
 * @returns {Promise<void>}
 */
async function onUpdateBudget({ row, budget }: { row: any; budget: number }): Promise<void> {
  if (!row?.campaign_id || !row?.profile_id) {
    ElMessage.error("缺少广告活动标识，无法修改预算");
    return;
  }
  if (!(budget > 0)) {
    ElMessage.error("预算必须大于 0");
    return;
  }
  const oldBudget = row.budget;
  try {
    await createManualBudgetAdjustment({
      campaign_id: row.campaign_id,
      profile_id: row.profile_id,
      budget_after: budget,
    });
    row.budget = budget;
    row._budgetInput = budget;
    ElMessage.success("预算修改已记录，待执行推送");
  } catch (error) {
    // 还原 UI 值，避免与后端不一致
    row.budget = oldBudget;
    row._budgetInput = oldBudget;
    console.error("[onUpdateBudget] 修改预算失败", error);
    ElMessage.error("修改预算失败");
  }
}

/**
 * 处理状态修改：调用后端 adjust-state 接口，成功后更新行内 state 字段。
 * 失败时还原 switch 状态。
 *
 * @param {Object} payload - { row, state }
 * @param {any} payload.row - 表格行数据
 * @param {string} payload.state - 目标状态（enabled / paused）
 * @returns {Promise<void>}
 */
async function onUpdateState({
  row,
  state,
}: {
  row: any;
  state: "enabled" | "paused";
}): Promise<void> {
  if (!row?.campaign_id || !row?.profile_id) {
    ElMessage.error("缺少广告活动标识，无法修改状态");
    return;
  }
  const oldState = row.state;
  try {
    await createCampaignStateAdjustment({
      campaign_id: row.campaign_id,
      profile_id: row.profile_id,
      state,
    });
    row.state = state;
    ElMessage.success(state === "enabled" ? "启用已记录，待执行推送" : "暂停已记录，待执行推送");
  } catch (error) {
    // 还原 UI 值，避免与后端不一致
    row.state = oldState;
    console.error("[onUpdateState] 修改状态失败", error);
    ElMessage.error("修改状态失败");
  }
}

loadTableData();

// ── 批量操作：调状态 / 调预算 ──────────────────────────────────────────────────────

const batchBudgetDialogVisible = ref(false);
const batchBudgetItems = ref<BatchBudgetItem[]>([]);
const batchBudgetCurrencyIcon = ref("$");

/**
 * 批量调整状态：将选中行的 campaign_id + profile_id + state 发送到后端。
 *
 * @param {Object} payload - { rows, state }
 * @param {any[]} payload.rows - 选中的表格行数据
 * @param {string} payload.state - 目标状态 enabled / paused
 * @returns {Promise<void>}
 */
async function onBatchState({
  rows,
  state,
}: {
  rows: any[];
  state: "enabled" | "paused";
}): Promise<void> {
  if (!rows.length) return;
  const items = rows.map((row) => ({
    campaign_id: row.campaign_id,
    profile_id: row.profile_id,
    state,
  }));
  try {
    const res = await batchAdjustCampaignState({ items });
    ElMessage.success(`批量调状态完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`);
    if (res.errors?.length) {
      res.errors.forEach((e) => ElMessage.warning(e.message));
    }
    loadTableData();
  } catch (error) {
    console.error("[onBatchState] 批量调状态失败", error);
    ElMessage.error("批量调状态失败");
  }
}

/**
 * 打开批量调预算对话框：将选中行转为 BatchBudgetItem 数组。
 *
 * @param {any[]} rows - 选中的表格行数据
 */
function onBatchBudgetOpen(rows: any[]): void {
  if (!rows.length) return;
  batchBudgetCurrencyIcon.value = rows[0].currency_icon || "$";
  batchBudgetItems.value = rows.map((row) => ({
    campaignId: row.campaign_id,
    profileId: row.profile_id,
    name: row.name || `活动 ${row.campaign_id}`,
    profileAlias: row.profile_alias || "",
    currentBudget: Number(row.budget) || 0,
  }));
  batchBudgetDialogVisible.value = true;
}

/**
 * 批量调预算确认：调用后端批量接口，成功后刷新表格。
 *
 * @param {Array} items - 每项含 campaignId + profileId + budget
 * @returns {Promise<void>}
 */
async function onBatchBudgetConfirm(
  items: Array<{ campaignId: string | number; profileId: string | number; budget: number }>
): Promise<void> {
  try {
    const res = await batchAdjustCampaignBudget({
      items: items.map((it) => ({
        campaign_id: it.campaignId,
        profile_id: it.profileId,
        budget_after: it.budget,
      })),
    });
    ElMessage.success(`批量调预算完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`);
    if (res.errors?.length) {
      res.errors.forEach((e) => ElMessage.warning(e.message));
    }
    loadTableData();
  } catch (error) {
    console.error("[onBatchBudgetConfirm] 批量调预算失败", error);
    ElMessage.error("批量调预算失败");
  }
}
</script>

<style scoped src="./ads.scss" lang="scss"></style>
