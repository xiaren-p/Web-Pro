/**
 * 亏损订单查询编排 composable：
 * - 持有 tableData / pagination / sortState / sync 状态
 * - 暴露 handleQuery / loadTableData / handleSortChange / 分页回调 / stopPolling
 * - 内部串联 fetchLossOrderSync + fetchLossOrderData，并按需启动/停止 3s 轮询
 *
 * 设计目标：让页面只负责组装 UI 与 v-model，所有"数据生命周期"全部封装在这里。
 */
import { ref, reactive, computed, onUnmounted, type Ref } from "vue";
import { ElMessage } from "element-plus";

import {
  fetchLossOrderSync,
  fetchLossOrderData,
  type LossOrderDataBody,
  type LossOrderSyncBody,
} from "@/api/lossmakingOrders";
import {
  ALL_SHOPS_VALUE,
  ALL_OWNERS_VALUE,
  applyFrontendRule,
  createRowMapper,
  formatDate,
  type ShopOptionRef,
} from "@/composables/lossmakingOrders/useLossOrderHelpers";

/** 页面暴露给 composable 的筛选模型形状（与 SearchForm 内部 v-model 保持一致）。 */
export interface LossOrderFilters {
  shops: string[];
  currency: string;
  owners: string[];
  orderDateRange: any;
  msku: string;
  rule: string;
}

/**
 * 创建亏损订单查询编排实例。
 *
 * @param filters - 页面侧筛选模型（reactive），用于读取查询参数
 * @param shopsRef - 店铺下拉项，用于 mapItemToRow 反查店铺名称
 */
export function useLossOrderQuery(filters: LossOrderFilters, shopsRef: ShopOptionRef) {
  const loading = ref(false);
  const tableData = ref<any[]>([]);
  const pagination = reactive({ current: 1, pageSize: 50, total: 0 });
  const sortState = reactive({ prop: "", order: "" });
  const syncTime = ref<string | null>(null);
  const syncing = ref(false);

  const syncTimeDisplay = computed(() => {
    if (!syncTime.value) return "-";
    try {
      const d = new Date(syncTime.value);
      const y = d.getFullYear();
      const m = d.getMonth() + 1;
      const day = d.getDate();
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      return `${y}/${m}/${day} ${hh}:${mm}:${ss}`;
    } catch {
      return syncTime.value || "-";
    }
  });

  const mapItemToRow = createRowMapper(shopsRef as Ref<any>);

  let pollTimer: number | null = null;

  /**
   * 把页面 params 翻译成后端 sync/data 接口入参，并执行一次"sync 取 key → data 取页"流程。
   */
  async function queryLossmakingOrders(params: any) {
    try {
      const body: any = { searchField: "seller_sku" };
      if (params.page) body.page = params.page;
      if (params.page_size) body.page_size = params.page_size;

      let startDate = params.start_date;
      let endDate = params.end_date;
      if (!startDate || !endDate) {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - 6);
        startDate = formatDate(start);
        endDate = formatDate(end);
      }
      body.startDate = startDate;
      body.endDate = endDate;

      if (params.shops && params.shops.length) {
        body.sids = params.shops.includes(ALL_SHOPS_VALUE) ? [] : params.shops;
      }
      if (params.msku) {
        const lines = String(params.msku)
          .split(/\r?\n/)
          .map((s) => s.trim())
          .filter(Boolean);
        if (lines.length > 0) body.searchValue = lines;
      }
      if (params.currency && params.currency !== "original") body.currencyCode = params.currency;
      if (params.owners && params.owners.length) {
        body.owners = params.owners.includes(ALL_OWNERS_VALUE) ? [] : params.owners;
      }
      if (params.rule) body.rule = params.rule;

      const syncBody: LossOrderSyncBody = {
        startDate: body.startDate,
        endDate: body.endDate,
        currencyCode: body.currencyCode,
      };
      const syncRes = await fetchLossOrderSync(syncBody);

      let dataRes: any = { list: [], total: 0, sync_time: syncRes && syncRes.sync_time };
      try {
        if (syncRes && syncRes.key) {
          const dataBody: LossOrderDataBody = { key: syncRes.key };
          if (body.page) dataBody.page = body.page;
          if (body.page_size) dataBody.page_size = body.page_size;
          if (body.owners !== undefined) dataBody.owners = body.owners;
          if (body.searchValue !== undefined) dataBody.searchValue = body.searchValue;
          if (body.rule) dataBody.rule = body.rule;
          if (body.sids !== undefined) dataBody.sids = body.sids;
          if (sortState.prop) {
            dataBody.sort_by = sortState.prop;
            dataBody.sort_order = sortState.order === "ascending" ? "asc" : "desc";
          }
          dataRes = await fetchLossOrderData(dataBody);
        }
      } catch (e) {
        console.error("lossmakingOrdersData error", e);
        dataRes = { list: [], total: 0, sync_time: syncRes && syncRes.sync_time };
      }

      try {
        const sr: any = syncRes;
        if (sr && sr.warning) ElMessage.warning(sr.warning || "部分数据已返回");
        if (sr && (sr.error || sr.msg)) ElMessage.error(sr.error || sr.msg || "后端返回错误信息");
      } catch {
        /* ignore */
      }

      return {
        list: dataRes.list || [],
        total: dataRes.total || 0,
        sync_time: (syncRes && syncRes.sync_time) || dataRes.sync_time || null,
        syncing: !!(syncRes && syncRes.syncing),
      };
    } catch (e) {
      console.error("queryLossmakingOrders error", e);
      return { list: [], total: 0, sync_time: null, syncing: false };
    }
  }

  /** 把当前 filters / pagination 组装成 params 发起一次后端查询并写回响应式状态。 */
  async function loadTableData() {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      currency: filters.currency,
      owners: filters.owners.includes(ALL_OWNERS_VALUE) ? [] : filters.owners,
      msku: filters.msku,
      rule: filters.rule,
    };
    if (filters.shops && filters.shops.length) {
      params.shops = filters.shops.includes(ALL_SHOPS_VALUE) ? [] : filters.shops;
    }
    if (filters.orderDateRange && filters.orderDateRange.length === 2) {
      const s = filters.orderDateRange[0];
      const e = filters.orderDateRange[1];
      params.start_date = typeof s === "string" ? s : formatDate(s as Date);
      params.end_date = typeof e === "string" ? e : formatDate(e as Date);
    }

    try {
      const res = await queryLossmakingOrders(params);
      const fullList = res.list || [];
      syncTime.value = res.sync_time || syncTime.value || null;

      const hasBackendList = Array.isArray(fullList) && fullList.length > 0;
      if (hasBackendList) {
        pagination.total = res.total || fullList.length;
        const previewed = applyFrontendRule(fullList, params.rule);
        tableData.value = (previewed || []).map((it: any) => mapItemToRow(it));
      } else {
        tableData.value = [];
        pagination.total = res.total || 0;
      }

      syncing.value = !!res.syncing;
      if (res.syncing) {
        startPolling(params);
      } else {
        stopPolling();
      }
    } catch (e) {
      console.error("查询数据失败", e);
      tableData.value = [];
      pagination.total = 0;
    }
  }

  /** 后端仍在同步缓存时，定时重试 sync 探测 syncing 是否已结束。 */
  function startPolling(_params: any) {
    if (pollTimer) return;
    pollTimer = window.setInterval(async () => {
      try {
        let startDate = _params.start_date;
        let endDate = _params.end_date;
        if (!startDate || !endDate) {
          const end = new Date();
          const start = new Date();
          start.setDate(end.getDate() - 6);
          startDate = formatDate(start);
          endDate = formatDate(end);
        }
        const syncRes = await fetchLossOrderSync({
          startDate,
          endDate,
          currencyCode:
            _params.currency && _params.currency !== "original" ? _params.currency : undefined,
        });
        if (syncRes && !syncRes.syncing) {
          syncing.value = false;
          stopPolling();
          await loadTableData();
        }
      } catch (e) {
        console.error("polling error", e);
      }
    }, 3000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function handleQuery() {
    loading.value = true;
    pagination.current = 1;
    await loadTableData();
    loading.value = false;
  }

  function handleSortChange({ prop, order }: { prop: string; order: string }) {
    try {
      sortState.prop = prop || "";
      sortState.order = order || "";
      pagination.current = 1;
      loadTableData();
    } catch (e) {
      console.error("handleSortChange error", e);
    }
  }

  function onPageChange(page: number) {
    pagination.current = page;
    loadTableData();
  }

  function onPageSizeChange(size: number) {
    pagination.pageSize = size;
    pagination.current = 1;
    loadTableData();
  }

  onUnmounted(() => stopPolling());

  return {
    loading,
    tableData,
    pagination,
    sortState,
    syncing,
    syncTime,
    syncTimeDisplay,
    handleQuery,
    loadTableData,
    handleSortChange,
    onPageChange,
    onPageSizeChange,
    stopPolling,
  };
}
