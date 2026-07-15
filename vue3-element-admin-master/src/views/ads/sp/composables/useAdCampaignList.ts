/**
 * 广告活动列表页业务逻辑 composable。
 *
 * @module useAdCampaignList
 * @description 封装筛选/分页/排序/列表加载/列配置/localStorage 缓存/预算与状态调整/批量操作。
 *              多个 watch 副作用（筛选持久化、国家-店铺联动、SKU 搜索类型联动）均在此管理。
 */

import { reactive, ref, computed, onMounted, watch } from "vue";
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

/** localStorage 缓存键常量。 */
const STORAGE_KEYS = {
  filters: "ADS_SP_FILTERS_V1",
  pagination: "ADS_SP_PAGINATION_V1",
  columns: "ADS_SP_COLUMNS_V1",
  overBudget: "ADS_SP_OVERBUDGET_V1",
  sort: "ADS_SP_SORT_V1",
} as const;

function readCache(key: string): unknown {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeCache(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 容量满或隐私模式：静默忽略
  }
}

export function useAdCampaignList() {
  // ── 状态 ──────────────────────────────────────────────────────────────────────
  const isLoading = ref(false);
  const tableData = ref([] as any[]);
  const total = ref(0);
  const summary = ref<Record<string, unknown> | null>(null);

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

  const _cachedSort = readCache(STORAGE_KEYS.sort) as { prop?: string; order?: string } | null;
  const sortParams = reactive({
    prop: _cachedSort?.prop || "",
    order: _cachedSort?.order || "",
  });

  const onlyOverBudget = ref<boolean>(
    (() => {
      const cached = readCache(STORAGE_KEYS.overBudget);
      return typeof cached === "boolean" ? cached : false;
    })()
  );

  const queueDrawerVisible = ref(false);
  const uploadDialogVisible = ref(false);

  // ── 筛选状态 ──────────────────────────────────────────────────────────────────
  function initFiltersFromCache(): Record<string, unknown> {
    const cached = readCache(STORAGE_KEYS.filters);
    // 优先读取子页面写入的最新日期（双向同步）
    const detailRange = readCache("ADS_SP_DATE_RANGE") as string[] | null;
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 7);
    const fmt = (d: Date) => {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const dd = String(d.getDate()).padStart(2, "0");
      return `${y}-${m}-${dd}`;
    };
    const defaultRange = [fmt(start), fmt(end)];
    const defaults = {
      countries: [] as string[],
      profiles: [] as string[],
      range: defaultRange,
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
      const c = cached as Record<string, unknown>;
      const merged: Record<string, unknown> = { ...defaults };
      for (const k of Object.keys(defaults)) {
        const v = c[k];
        // range 特殊处理：只接受有效的 2 元素数组，否则保留默认 7 天
        if (k === "range") {
          if (Array.isArray(v) && v.length === 2) merged[k] = v;
          continue;
        }
        if (Array.isArray(defaults[k as keyof typeof defaults])) {
          if (Array.isArray(v)) merged[k] = v;
        } else if (typeof v === "string") {
          merged[k] = v;
        }
      }
      // 用子页面写入的最新日期覆盖（双向同步）
      if (Array.isArray(detailRange) && detailRange.length === 2 && detailRange[0]) {
        merged.range = detailRange;
      }
      return merged;
    }
    // 无筛选缓存：用子页面写入的最新日期覆盖默认范围
    if (Array.isArray(detailRange) && detailRange.length === 2 && detailRange[0]) {
      defaults.range = detailRange;
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

  // ── 下拉选项 ──────────────────────────────────────────────────────────────────
  const countries = ref<{ value: string; label: string }[]>([]);
  const profiles = ref<{ value: string; label: string; country?: string }[]>([]);
  const portfolios = ref<{ value: string; label: string }[]>([]);
  const biddingTypes = ref<{ value: string; label: string }[]>([]);
  const owners = ref<{ value: string; label: string }[]>([]);
  const tagsList = ref<any[]>([]);
  const campaignStatuses = ref<any[]>([]);
  const serviceStatuses = ref<any[]>([]);

  const filteredProfiles = computed(() => {
    if (!filters.countries || filters.countries.length === 0) return profiles.value;
    const selectedSet = new Set(filters.countries);
    return profiles.value.filter((p) => selectedSet.has(p.country ?? ""));
  });

  const allSkus = ref<any[]>([]);
  const skuOptions = ref<any[]>([]);

  // ── 列配置 ────────────────────────────────────────────────────────────────────
  const defaultColumns = [
    { label: "服务状态", prop: "service_status", visible: true, category: "设置", sortable: false },
    { label: "竞价策略", prop: "bidding_type", visible: true, category: "设置", sortable: false },
    { label: "广告组合", prop: "portfolio_name", visible: true, category: "设置", sortable: false },
    { label: "预算", prop: "budget", visible: true, category: "设置", sortable: true },
    { label: "开始日期", prop: "startDate", visible: true, category: "设置", sortable: true },
    { label: "标签", prop: "tags", visible: true, category: "设置", sortable: false },
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
    { label: "广告笔单价", prop: "adsOrderPrice", visible: true, category: "转化", sortable: true },
    { label: "广告销量", prop: "adsVolume", visible: true, category: "转化", sortable: true },
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
  const columnConfigVisible = ref(false);

  function restoreDefaultColumns() {
    columnConfigVisible.value = true;
  }

  function onColumnConfigSave(columns: any[]) {
    activeColumns.value = columns;
    writeCache(STORAGE_KEYS.columns, columns);
    ElMessage.success("列配置已保存");
  }

  // ── 数据加载 ──────────────────────────────────────────────────────────────────
  async function loadTableData() {
    isLoading.value = true;
    try {
      const params: any = {
        pageNum: currentPage.value,
        pageSize: pageSize.value,
        name: filters.campaignName,
        state: filters.campaignStatus.join(","),
        service_status: onlyOverBudget.value
          ? filters.serviceStatus.length
            ? `${filters.serviceStatus.join(",")},CAMPAIGN_OUT_OF_BUDGET`
            : "CAMPAIGN_OUT_OF_BUDGET"
          : filters.serviceStatus.join(","),
        sponsored_type: filters.adsTypes.join(","),
        portfolio_id: filters.portfolios.join(","),
        bidding_type: filters.biddingType,
        tags: filters.tags.join(","),
        owners: filters.owners.join(","),
        profiles: filters.profiles.join(","),
        countries: filters.countries.join(","),
        date_start: filters.range?.[0] || "",
        date_end: filters.range?.[1] || "",
        skus: filters.skus.join(","),
        asinSearchType: filters.asinSearchType,
      };

      if (sortParams.prop && sortParams.order) {
        params.sort_prop = sortParams.prop;
        params.sort_order = sortParams.order === "ascending" ? "asc" : "desc";
      }

      const res = await getAdCampaigns(params);
      tableData.value = res.list || [];
      total.value = res.total || 0;
      summary.value = res.summary ?? null;

      writeCache(STORAGE_KEYS.pagination, {
        pageSize: pageSize.value,
        currentPage: currentPage.value,
      });
    } catch (error) {
      console.error(error);
      ElMessage.error("获取广告列表数据失败");
    } finally {
      isLoading.value = false;
    }
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

  // ── 队列/上传 ──────────────────────────────────────────────────────────────────
  function handleNewAdCommand(command: string): void {
    if (command === "upload") {
      uploadDialogVisible.value = true;
    }
  }

  // ── 选项加载 ──────────────────────────────────────────────────────────────────
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

  function buildParentAsinOptions(options: any[]): any[] {
    return options
      .filter((item: any) => {
        const code = String(item.code || "");
        const parentAsin = String(item.parent || item.parent_asin || "");
        return code && parentAsin && code === parentAsin;
      })
      .map((item: any) => {
        const parentAsin = String(item.parent || item.parent_asin || item.code);
        return { ...item, value: parentAsin, label: parentAsin, code: parentAsin };
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
    // 搜索时全量过滤，不限制
    skuOptions.value = sourceOptions.filter((s: any) =>
      `${s.title || ""}${s.code || ""}${s.value || ""}`.toLowerCase().includes(q)
    );
  }

  function remoteSearchSku(query: string) {
    syncSkuOptions(query);
  }

  async function loadSkuOptions(): Promise<void> {
    try {
      const res = await getAdSkuOptions({});
      allSkus.value = res.skus || [];
      syncSkuOptions("");
    } catch (error) {
      console.error("加载 SKU 下拉失败", error);
    }
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

  // ── 预算/状态调整 ──────────────────────────────────────────────────────────────
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
      row.budget = oldBudget;
      row._budgetInput = oldBudget;
      console.error("[onUpdateBudget] 修改预算失败", error);
      ElMessage.error("修改预算失败");
    }
  }

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
      row.state = oldState;
      console.error("[onUpdateState] 修改状态失败", error);
      ElMessage.error("修改状态失败");
    }
  }

  // ── 批量操作 ──────────────────────────────────────────────────────────────────
  const batchBudgetDialogVisible = ref(false);
  const batchBudgetItems = ref<any[]>([]);
  const batchBudgetCurrencyIcon = ref("$");

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
      ElMessage.success(
        `批量调状态完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`
      );
      if (res.errors?.length) {
        res.errors.forEach((e) => ElMessage.warning(e.message));
      }
      loadTableData();
    } catch (error) {
      console.error("[onBatchState] 批量调状态失败", error);
      ElMessage.error("批量调状态失败");
    }
  }

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
      ElMessage.success(
        `批量调预算完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`
      );
      if (res.errors?.length) {
        res.errors.forEach((e) => ElMessage.warning(e.message));
      }
      loadTableData();
    } catch (error) {
      console.error("[onBatchBudgetConfirm] 批量调预算失败", error);
      ElMessage.error("批量调预算失败");
    }
  }

  // ── Watchers ──────────────────────────────────────────────────────────────────
  watch(onlyOverBudget, (v) => {
    writeCache(STORAGE_KEYS.overBudget, v);
    currentPage.value = 1;
    loadTableData();
  });

  watch(
    filters,
    (v) => {
      writeCache(STORAGE_KEYS.filters, { ...v });
      writeCache("ADS_SP_DATE_RANGE", v.range);
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

  // ── 初始化 ────────────────────────────────────────────────────────────────────
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

  loadTableData();

  return {
    isLoading,
    tableData,
    total,
    pageSize,
    currentPage,
    sortParams,
    onlyOverBudget,
    summary,
    queueDrawerVisible,
    uploadDialogVisible,
    filters,
    countries,
    profiles,
    portfolios,
    biddingTypes,
    owners,
    tagsList,
    campaignStatuses,
    serviceStatuses,
    filteredProfiles,
    skuOptions,
    defaultColumns,
    activeColumns,
    tableColumns,
    columnConfigVisible,
    restoreDefaultColumns,
    onColumnConfigSave,
    loadTableData,
    search,
    resetFilters,
    handlePageChange,
    handlePageSizeChange,
    handleSortChange,
    openSearchTemplates,
    handleNewAdCommand,
    remoteSearchSku,
    remoteSearchPortfolio,
    onUpdateBudget,
    onUpdateState,
    onBatchState,
    onBatchBudgetOpen,
    onBatchBudgetConfirm,
    batchBudgetDialogVisible,
    batchBudgetItems,
    batchBudgetCurrencyIcon,
  };
}
