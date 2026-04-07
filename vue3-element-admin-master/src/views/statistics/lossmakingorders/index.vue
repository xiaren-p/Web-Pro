<template>
  <div class="page-container app-container">
    <!-- 搜索区域（采用 listing 的样式） -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="filters" :inline="true">
        <el-form-item label="店铺">
          <el-select
            v-model="filters.shops"
            multiple
            placeholder="请选择店铺"
            style="min-width: 120px"
          >
            <el-option v-if="shops.length" label="全选" :value="ALL_SHOPS_VALUE"></el-option>
            <el-option v-for="s in shops" :key="s.value" :value="s.value">
              <template #default>
                <span>{{ s.label }}</span>
                <span style="margin-left: 8px; color: #999">{{ s.country }}</span>
              </template>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="币种">
          <el-select v-model="filters.currency" placeholder="请选择币种" style="width: 100px">
            <el-option v-for="c in currencies" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="Listing 负责人">
          <el-select
            v-model="filters.owners"
            multiple
            placeholder="请选择负责人"
            style="min-width: 140px"
          >
            <el-option v-if="owners.length" label="全选" :value="ALL_OWNERS_VALUE"></el-option>
            <el-option v-for="o in owners" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="下单时间">
          <el-date-picker
            v-model="filters.orderDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :shortcuts="dateShortcuts"
            unlink-panels
          ></el-date-picker>
        </el-form-item>

        <el-form-item label="规则">
          <div style="display: flex; gap: 8px; align-items: center">
            <el-select v-model="filters.rule" placeholder="请选择规则" style="width: 140px">
              <el-option label="规则一" value="rule1" />
              <el-option label="规则二" value="rule2" />
              <el-option label="规则三" value="rule3" />
              <el-option label="规则四" value="rule4" />
            </el-select>
            <el-tooltip effect="dark" placement="top" :show-after="200">
              <template #content>
                <div
                  v-if="filters.rule"
                  style="max-width: 360px; font-size: 12px; line-height: 1.4; white-space: pre-wrap"
                >
                  {{ ruleDescription(filters.rule) }}
                </div>
              </template>
              <i class="rule-help" aria-hidden="true">?</i>
            </el-tooltip>
          </div>
        </el-form-item>

        <!-- 搜索行（仿 listing） -->
        <el-form-item label="搜索" prop="msku" class="search-row">
          <el-popover
            v-model:visible="mskuPopoverVisible"
            placement="bottom-end"
            width="245"
            trigger="click"
            popper-class="popover-advanced-input"
          >
            <template #default>
              <div class="popover-body">
                <el-input
                  v-model="mskuPopoverText"
                  type="textarea"
                  placeholder="精确搜索，一行一项，最多支持2000行"
                  :rows="6"
                  show-word-limit
                  maxlength="200000"
                />
                <div class="popover-btn ak-align-center" style="margin-top: 8px">
                  <button
                    type="button"
                    class="el-button el-button--default el-button--mini is-round"
                    @click="mskuClear"
                  >
                    清空
                  </button>
                  <div class="popover-btn-right" style="display: inline-block; margin-left: 8px">
                    <button
                      type="button"
                      class="el-button el-button--default el-button--mini is-round"
                      @click="mskuClose"
                    >
                      关闭
                    </button>
                    <button
                      type="button"
                      class="el-button el-button--primary el-button--mini is-plain is-round"
                      @click="applyMskuSearch"
                    >
                      搜索
                    </button>
                  </div>
                </div>
              </div>
            </template>

            <template #reference>
              <el-input
                v-model="filters.msku"
                placeholder="输入 MSKU"
                clearable
                style="width: 240px"
                @keyup.enter="handleQuery"
                @click.stop="openMskuPopover"
              />
            </template>
          </el-popover>

          <el-button type="primary" icon="search" style="margin-left: 8px" @click="handleQuery">
            搜索
          </el-button>
          <el-button class="ml-2" icon="refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格区域 -->
    <el-card shadow="hover" class="data-table mt-4">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button type="primary" plain icon="download">导出</el-button>
        </div>
        <div class="data-table__toolbar--meta">
          <span class="sync-time">
            <template v-if="syncing">
              <div style="display: inline-block">
                正在同步
                <span class="sync-spinner" aria-hidden="true"></span>
              </div>
              <div class="sync-last">上次同步时间：{{ syncTimeDisplay }}</div>
            </template>
            <template v-else>数据同步时间：{{ syncTimeDisplay }}</template>
          </span>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        class="data-table__content"
        border
        stripe
        max-height="520"
        @sort-change="handleSortChange"
      >
        <el-table-column label="图片" fixed="left" width="100" align="center">
          <template #default="{ row }">
            <el-image :src="row.image" fit="cover" style="width: 36px; height: 36px" />
          </template>
        </el-table-column>
        <el-table-column label="MSKU" fixed="left" width="140">
          <template #default="{ row }">
            <div v-if="row.msku && row.msku.length" class="msku-cell">
              <div v-for="(m, i) in row.msku" :key="i" class="msku-item">
                <span class="copy-wrap">
                  <el-tooltip effect="dark" :content="m" placement="top" :show-after="500">
                    <span
                      class="text"
                      :class="{
                        'msku-rule2': row.matched_rule === 'rule2',
                        'msku-rule3': row.matched_rule === 'rule3',
                        'msku-rule4': row.matched_rule === 'rule4',
                      }"
                      @dblclick.stop="copyOnDblClick(m)"
                    >
                      {{ m }}
                    </span>
                  </el-tooltip>
                </span>
              </div>
            </div>
            <div v-else class="msku-cell">-</div>
          </template>
        </el-table-column>
        <el-table-column label="ASIN" fixed="left" width="140">
          <template #default="{ row }">
            <div class="multiline">
              <div v-if="row.asin && row.asin.length">
                <div v-for="(a, i) in row.asin" :key="i">
                  <span class="copy-wrap">
                    <span class="text" @dblclick.stop="copyOnDblClick(a)">{{ a }}</span>
                  </span>
                </div>
              </div>
              <div v-else>-</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="父ASIN" width="140">
          <template #default="{ row }">
            <div class="multiline">
              <div v-if="row.parent_asin && row.parent_asin.length">
                <div v-for="(p, i) in row.parent_asin" :key="i">
                  <span class="copy-wrap">
                    <span class="text" @dblclick.stop="copyOnDblClick(p)">{{ p }}</span>
                  </span>
                </div>
              </div>
              <div v-else>-</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="店铺/国家" width="140">
          <template #default="{ row }">
            <div class="two-line-cell">
              <div class="line1">{{ row.shop_label || "-" }}</div>
              <div v-if="row.shop_country" class="line2">{{ row.shop_country }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="品名/SKU" min-width="220">
          <template #default="{ row }">
            <div class="multiline">
              <div v-if="row.title_sku_pairs && row.title_sku_pairs.length">
                <div v-for="(pair, i) in row.title_sku_pairs" :key="i">
                  <el-tooltip
                    effect="dark"
                    :content="(pair.name || '') + (pair.sku ? '\n' + pair.sku : '')"
                    placement="top"
                    :show-after="500"
                  >
                    <div class="two-line-cell">
                      <div class="line1">{{ pair.name }}</div>
                      <div class="line2">{{ pair.sku }}</div>
                    </div>
                  </el-tooltip>
                </div>
              </div>
              <div v-else>-</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="gross_profit"
          label="毛利润"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ row.currency_icon || "" }}{{ row.gross_profit || "-" }}
          </template>
        </el-table-column>
        <el-table-column
          prop="gross_margin"
          label="毛利率"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">{{ formatPercent(row.gross_margin) }}</template>
        </el-table-column>
        <el-table-column
          prop="net_gross_margin"
          label="净毛利率"
          width="130"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">{{ formatPercent(row.net_gross_margin) }}</template>
        </el-table-column>
        <el-table-column
          prop="return_rate"
          label="退货率"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">{{ formatPercent(row.return_rate) }}</template>
        </el-table-column>
        <el-table-column
          prop="refund_amount_rate"
          label="退款率"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">{{ formatPercent(row.refund_amount_rate) }}</template>
        </el-table-column>
        <el-table-column
          prop="total_stock_fee"
          label="仓储费"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ row.currency_icon || "" }}{{ row.total_stock_fee || "-" }}
          </template>
        </el-table-column>
        <el-table-column
          prop="spend"
          label="广告费"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ row.currency_icon || "" }}{{ row.spend || "-" }}
          </template>
        </el-table-column>
        <el-table-column
          prop="spend_rate"
          label="广告率费"
          width="130"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
          sortable="custom"
        >
          <template #default="{ row }">{{ formatPercent(row.spend_rate) }}</template>
        </el-table-column>

        <el-table-column
          label="负责人"
          fixed="right"
          width="120"
          align="center"
          class-name="col-center"
          header-class-name="col-center"
        >
          <template #default="{ row }">
            <div class="multiline">
              <div v-if="row.principal_names && row.principal_names.length">
                <div v-for="(p, i) in row.principal_names" :key="i">{{ p }}</div>
              </div>
              <div v-else>-</div>
            </div>
          </template>
        </el-table-column>

        <!-- 操作列已移除 -->
      </el-table>

      <div class="flex-x-end mt-3">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          :current-page="pagination.current"
          :page-size="pagination.pageSize"
          :page-sizes="[50, 100, 200]"
          @size-change="onPageSizeChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from "vue";
import { ShopsAPI } from "@/backend";
import { ElMessage } from "element-plus";

defineOptions({ name: "LossmakingOrders" });

const queryFormRef = ref();
const loading = ref(false);

// 默认下单时间：最近7天（含今天）
const defaultEndDate = new Date();
const defaultStartDate = new Date();
defaultStartDate.setDate(defaultEndDate.getDate() - 6);

const getShops = async () => {
  try {
    const res = await ShopsAPI.getOptions();
    return (res || []).map((it: any) => ({ id: it.id, name: it.name, country: it.country }));
  } catch (e) {
    console.error("getShops error", e);
    return [];
  }
};

const getListingOwners = async () => {
  try {
    const res = await ShopsAPI.getOwners();
    return (res || []).map((it: any) => ({
      id: it.id || it.value,
      name: it.label || it.name || it.realname,
    }));
  } catch (e) {
    console.error("getListingOwners error", e);
    return [];
  }
};

const queryLossmakingOrders = async (params: any) => {
  try {
    // 构造请求体，后端会处理分页合并（前端不发送 offset/length）
    const body: any = {
      searchField: "seller_sku",
    };
    // include pagination params if provided by frontend
    if (params.page) body.page = params.page;
    if (params.page_size) body.page_size = params.page_size;
    // ensure startDate/endDate present — default to recent 7 days when missing
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
      // 过滤掉特殊全选标记
      body.sids = params.shops.includes(ALL_SHOPS_VALUE) ? [] : params.shops;
    }
    if (params.msku) {
      // 支持多行输入
      const lines = String(params.msku)
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter(Boolean);
      if (lines.length > 0) body.searchValue = lines;
    }
    if (params.currency && params.currency !== "original") body.currencyCode = params.currency;
    if (params.owners && params.owners.length)
      body.owners = params.owners.includes(ALL_OWNERS_VALUE) ? [] : params.owners;
    // forward selected rule to backend so backend can apply server-side rule filtering
    if (params.rule) body.rule = params.rule;

    // 迁移到后端缓存模型：先调用 sync 接口获取 cache key 与同步状态，再用 data 接口读取缓存页数据
    const syncBody: any = {
      // 后端 cache key 只基于 startDate/endDate/currencyCode（不传入前端过滤参数）
      startDate: body.startDate,
      endDate: body.endDate,
      currencyCode: body.currencyCode,
    };

    const syncRes = await (await import("@/backend")).StatisticsAPI.lossmakingOrdersSync(syncBody);
    // 初始值：如果没有 key，则无法读取缓存
    let dataRes: any = { list: [], total: 0, sync_time: syncRes && syncRes.sync_time };
    try {
      if (syncRes && syncRes.key) {
        const dataBody: any = { key: syncRes.key };
        if (body.page) dataBody.page = body.page;
        if (body.page_size) dataBody.page_size = body.page_size;
        // forward optional frontend filters to data endpoint for server-side filtering
        if (body.owners !== undefined) dataBody.owners = body.owners;
        if (body.searchValue !== undefined) dataBody.searchValue = body.searchValue;
        if (body.rule) dataBody.rule = body.rule;
        // forward selected shops (sids) to data endpoint so backend can filter by item.sids
        if (body.sids !== undefined) dataBody.sids = body.sids;
        // forward sorting state to data endpoint (asc/desc)
        if (sortState.prop) {
          dataBody.sort_by = sortState.prop;
          dataBody.sort_order = sortState.order === "ascending" ? "asc" : "desc";
        }
        dataRes = await (await import("@/backend")).StatisticsAPI.lossmakingOrdersData(dataBody);
      }
    } catch (e) {
      console.error("lossmakingOrdersData error", e);
      dataRes = { list: [], total: 0, sync_time: syncRes && syncRes.sync_time };
    }
    // 将 sync 元信息与分页数据合并返回给调用者
    try {
      const sr: any = syncRes as any;
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
    return { list: [], total: 0 };
  }
};

// 常量
const ALL_SHOPS_VALUE = "__ALL__";
const ALL_OWNERS_VALUE = "__ALL_OWNERS__";

// 币种列表（含原币种选项）
const currencies = [
  { label: "原币种", value: "original" },
  { label: "CNY", value: "CNY" },
  { label: "USD", value: "USD" },
  { label: "EUR", value: "EUR" },
  { label: "JPY", value: "JPY" },
  { label: "AUD", value: "AUD" },
  { label: "CAD", value: "CAD" },
  { label: "MXN", value: "MXN" },
  { label: "GBP", value: "GBP" },
  { label: "INR", value: "INR" },
  { label: "AED", value: "AED" },
  { label: "SGD", value: "SGD" },
  { label: "SAR", value: "SAR" },
  { label: "BRL", value: "BRL" },
  { label: "SEK", value: "SEK" },
  { label: "PLN", value: "PLN" },
  { label: "TRY", value: "TRY" },
  { label: "HKD", value: "HKD" },
];

// 筛选模型
const filters = reactive({
  shops: [] as string[],
  currency: "EUR",
  owners: [] as string[],
  // `el-date-picker` expects a string[] or Date[] for v-model; use `any` to satisfy TS while
  // keeping runtime values as Date objects when needed.
  orderDateRange: [defaultStartDate, defaultEndDate] as any,
  msku: "",
  rule: "rule1",
});

// MSKU 多行弹窗状态与文本
const mskuPopoverText = ref("");
const mskuPopoverVisible = ref(false);

function openMskuPopover() {
  mskuPopoverText.value = filters.msku || "";
  mskuPopoverVisible.value = true;
}

function mskuClear() {
  mskuPopoverText.value = "";
}

function mskuClose() {
  mskuPopoverVisible.value = false;
}

function applyMskuSearch() {
  try {
    const lines = String(mskuPopoverText.value || "")
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (lines.length > 2000) {
      ElMessage.warning("最多支持2000行，已自动截断到前2000行");
      const truncated = lines.slice(0, 2000);
      filters.msku = truncated.join("\n");
    } else {
      filters.msku = lines.join("\n");
    }
    mskuPopoverVisible.value = false;
    // 触发查询
    handleQuery();
  } catch (e) {
    console.error("applyMskuSearch error", e);
    ElMessage.error("搜索失败");
  }
}

// 搜索仅支持 MSKU（移除搜索类型选择）

const shops = ref<Array<{ label: string; value: string; country?: string }>>([]);
const owners = ref<Array<{ label: string; value: string }>>([]);

const tableData = ref<any[]>([]);
const pagination = reactive({ current: 1, pageSize: 50, total: 0 });
const sortState = reactive({ prop: "", order: "" });
const syncTime = ref<string | null>(null);
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
    // 格式 YYYY/M/D HH:mm:ss（示例：2026/1/19 14:57:22）
    return `${y}/${m}/${day} ${hh}:${mm}:${ss}`;
  } catch {
    return syncTime.value || "-";
  }
});

// 同步状态与轮询句柄
const syncing = ref(false);
let pollTimer: number | null = null;

function startPolling(params: any) {
  if (pollTimer) return;
  pollTimer = window.setInterval(async () => {
    try {
      const body: any = {
        searchField: "seller_sku",
      };
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
      if (params.shops && params.shops.length)
        body.sids = params.shops.includes(ALL_SHOPS_VALUE) ? [] : params.shops;
      if (params.msku) {
        const lines = String(params.msku)
          .split(/\r?\n/)
          .map((s) => s.trim())
          .filter(Boolean);
        if (lines.length > 0) body.searchValue = lines;
      }
      if (params.currency && params.currency !== "original") body.currencyCode = params.currency;
      if (params.owners && params.owners.length)
        body.owners = params.owners.includes(ALL_OWNERS_VALUE) ? [] : params.owners;
      if (params.rule) body.rule = params.rule;

      const syncRes = await (
        await import("@/backend")
      ).StatisticsAPI.lossmakingOrdersSync({
        startDate: body.startDate,
        endDate: body.endDate,
        currencyCode: body.currencyCode,
      });
      if (syncRes && !syncRes.syncing) {
        // 同步完成，停止轮询并刷新表格
        syncing.value = false;
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
        await loadTableData();
      }
    } catch (e) {
      // 忽略轮询错误，但保留继续尝试
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

onUnmounted(() => {
  stopPolling();
});

// 处理表格排序事件（Element Plus 会触发 sort-change）
function handleSortChange({ prop, order }: any) {
  try {
    sortState.prop = prop || "";
    sortState.order = order || "";
    pagination.current = 1;
    // 重新加载第一页数据（后端会按 sort_by/sort_order 返回）
    loadTableData();
  } catch (e) {
    console.error("handleSortChange error", e);
  }
}

// helper to compute numeric values robustly
function parseNumber(v: any) {
  try {
    if (v === null || v === undefined || v === "") return NaN;
    if (typeof v === "number") return v;
    const s = String(v)
      .replace(/,/g, "")
      .replace(/[^0-9.\-eE]/g, "");
    const n = parseFloat(s);
    return isNaN(n) ? NaN : n;
  } catch {
    return NaN;
  }
}

// 将后端 item 映射成表格行的函数，便于复用与测试
function mapItemToRow(it: any) {
  // normalize MSKU/ASIN/local infos from backend (compat with pick_fields)
  // prefer backend-provided price_list when available; fall back to older mskus/asins
  const price_list = it.price_list || [];
  const msku =
    Array.isArray(price_list) && price_list.length
      ? price_list.map((p: any) => p && (p.local_sku || p.sku)).filter(Boolean)
      : it.seller_sku
        ? Array.isArray(it.seller_sku)
          ? it.seller_sku
          : [it.seller_sku]
        : [];
  const asin =
    Array.isArray(price_list) && price_list.length
      ? price_list.map((p: any) => p && p.asin).filter(Boolean)
      : it.asin
        ? Array.isArray(it.asin)
          ? it.asin
          : [it.asin]
        : [];
  const parent_asin = it.parent_asins || [];
  const raw_local_infos = it.local_infos || [];
  const local_infos = Array.isArray(raw_local_infos)
    ? raw_local_infos
        .map((li: any) => {
          if (!li) return null;
          if (typeof li === "string") return { local_name: "", local_sku: li };
          return {
            local_name: li.local_name || li.name || "",
            local_sku: li.local_sku || li.sku || "",
          };
        })
        .filter(Boolean)
    : [];
  const title_sku_pairs = local_infos
    .map((li: any) => ({
      name: li.local_name || "",
      sku: li.local_sku || "",
    }))
    .filter((p: any) => p.name || p.sku);

  // principal_names may be string (comma/newline separated) or array
  const raw_principals = it.principal_names || it.principals || it.principal || [];
  let principal_names: string[] = [];
  if (Array.isArray(raw_principals)) {
    principal_names = raw_principals.map((p: any) => String(p).trim()).filter(Boolean);
  } else if (typeof raw_principals === "string") {
    principal_names = raw_principals
      .split(/[\n,;]+/)
      .map((s: string) => s.trim())
      .filter(Boolean);
  } else if (raw_principals) {
    principal_names = [String(raw_principals)];
  }

  // seller_store_countries can be array of objects or array of strings
  const raw_countries = it.seller_store_countries || [];
  const country_names = Array.isArray(raw_countries)
    ? raw_countries
        .map((c: any) => (typeof c === "string" ? c : (c && (c.name || c.label)) || ""))
        .filter(Boolean)
    : [];

  let shop_label = "";
  let shop_country = "";
  try {
    const sid = (it.sids && it.sids[0]) || null;
    if (sid) {
      const found = shops.value.find((s) => String(s.value) === String(sid));
      if (found) {
        shop_label = found.label || String(sid);
        shop_country = found.country || "";
      } else if (country_names.length) {
        shop_label = country_names[0];
        shop_country = "";
      } else {
        shop_label = String(sid);
        shop_country = "";
      }
    } else if (country_names.length) {
      shop_label = country_names[0];
      shop_country = "";
    }
  } catch {
    shop_label = "";
    shop_country = "";
  }

  const imageFallback = ((): string => {
    if (it.small_image_url) return it.small_image_url;
    if (Array.isArray(price_list) && price_list.length) {
      for (const p of price_list) {
        if (!p) continue;
        if (p.small_main_image_url) return p.small_main_image_url;
        if (p.small_image_url) return p.small_image_url;
        if (p.small_image) return p.small_image;
      }
    }
    return "";
  })();
  // compute matched rule for highlighting (rule2: all three; rule3: cond1+cond2; rule4: cond1+cond3)
  const gross_profit_num = parseNumber(it.gross_profit);
  const refund_amount_rate_num = parseNumber(it.refund_amount_rate);
  const spend_rate_num = parseNumber(it.spend_rate);
  const cond1 = !isNaN(gross_profit_num) && gross_profit_num < 0;
  const cond2 = !isNaN(refund_amount_rate_num) && refund_amount_rate_num > 0.15;
  const cond3 = !isNaN(spend_rate_num) && spend_rate_num > 0.1;
  let matched_rule: string | null = null;
  if (cond1 && cond2 && cond3) matched_rule = "rule2";
  else if (cond1 && cond2) matched_rule = "rule3";
  else if (cond1 && cond3) matched_rule = "rule4";

  return {
    image: imageFallback,
    msku: Array.isArray(msku) ? msku : [msku].filter(Boolean),
    asin: Array.isArray(asin) ? asin : [asin].filter(Boolean),
    parent_asin: Array.isArray(parent_asin) ? parent_asin : [parent_asin].filter(Boolean),
    title_sku_pairs,
    title_sku: title_sku_pairs.map((p: any) => (p.name || "") + (p.sku ? " / " + p.sku : "")),
    principal_names,
    shop_label,
    shop_country,
    currency_icon: it.currency_icon || it.currency_code || "",
    gross_profit: it.gross_profit,
    gross_margin: it.gross_margin,
    net_gross_margin: it.net_gross_margin,
    return_rate: it.return_rate,
    refund_amount_rate: it.refund_amount_rate,
    total_stock_fee: it.total_stock_fee,
    spend: it.spend,
    spend_rate: it.spend_rate,
    // annotation used for row highlighting
    matched_rule,
  };
}

// return a CSS class name for a given row based on matched_rule
// rowClassName removed — highlighting is applied per-MSKU element now

// 前端规则占位：如果需要客户端做二次筛选或预览规则，可在此实现
function applyFrontendRule(items: any[], rule: string | null) {
  if (!rule) return items;
  try {
    // 当前为占位实现：直接返回
    return items;
  } catch {
    return items;
  }
}

function ruleDescription(rule: string | null) {
  if (!rule) return "";
  if (rule === "rule1")
    return "规则一：满足任一条件 — 毛利润 < 0，或 退款率 > 15%，或 广告费率 > 10%";
  if (rule === "rule2")
    return "规则二：同时满足三项条件 — 毛利润 < 0 且 退款率 > 15% 且 广告费率 > 10%";
  if (rule === "rule3") return "规则三：满足毛利润 < 0 且 退款率 > 15%";
  if (rule === "rule4") return "规则四：满足毛利润 < 0 且 广告费率 > 10%";
  return "";
}

// 日期快捷选项：写入 Date 对象到 filters.orderDateRange，确保 v-model 立即反映
// 尝试让面板立即确认并关闭：先写入 v-model（Date），再调用若干可能存在的确认/关闭方法
function emitPickerPick(picker: any, start: Date, end: Date) {
  try {
    if (!picker) return;
    // 优先把 v-model 写入，让面板数据就位
    filters.orderDateRange = [start, end];

    const tryCall = (obj: any, name: string) => {
      try {
        if (!obj) return false;
        const fn = obj[name];
        if (typeof fn === "function") {
          fn.call(obj);
          return true;
        }
      } catch {
        // ignore
      }
      return false;
    };

    const methodCandidates = [
      "confirm",
      "handleConfirm",
      "doConfirm",
      "onConfirm",
      "hidePicker",
      "close",
      "closePicker",
      "togglePicker",
    ];

    for (const m of methodCandidates) {
      if (tryCall(picker, m)) return;
      if (picker.proxy && tryCall(picker.proxy, m)) return;
      if (picker.component && tryCall(picker.component, m)) return;
    }

    // fallback: try emitting if available (some versions support emit)
    if (typeof picker.emit === "function") {
      try {
        picker.emit("pick", [start, end]);
      } catch {
        /* ignore */
      }
      try {
        picker.emit("confirm");
      } catch {
        /* ignore */
      }
    }
  } catch {
    // swallow
  }
}

const dateShortcuts = [
  {
    text: "今天",
    onClick: (picker: any) => {
      const end = new Date();
      const start = new Date();
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "昨天",
    onClick: (picker: any) => {
      const d = new Date();
      d.setDate(d.getDate() - 1);
      emitPickerPick(picker, d, d);
      filters.orderDateRange = [d, d];
    },
  },
  {
    text: "最近7天",
    onClick: (picker: any) => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 6);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "最近30天",
    onClick: (picker: any) => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "本月",
    onClick: (picker: any) => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "上月",
    onClick: (picker: any) => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "今年",
    onClick: (picker: any) => {
      const now = new Date();
      const start = new Date(now.getFullYear(), 0, 1);
      const end = new Date(now.getFullYear(), 11, 31);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
  {
    text: "去年",
    onClick: (picker: any) => {
      const now = new Date();
      const start = new Date(now.getFullYear() - 1, 0, 1);
      const end = new Date(now.getFullYear() - 1, 11, 31);
      emitPickerPick(picker, start, end);
      filters.orderDateRange = [start, end];
    },
  },
];

function formatDate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// 页面初始化：获取店铺与负责人
onMounted(async () => {
  try {
    const s = await getShops();
    shops.value = (s || []).map((x: any) => ({
      label: x.name || x.label || x.shop,
      value: x.id || x.value || x.shop,
      country: x.country,
    }));
  } catch (e) {
    console.error("获取店铺失败", e);
  }

  try {
    const o = await getListingOwners();
    owners.value = (o || []).map((x: any) => ({
      label: x.name || x.label,
      value: x.id || x.value,
    }));
  } catch (e) {
    console.error("获取负责人失败", e);
  }

  await handleQuery();
});

async function handleQuery() {
  loading.value = true;
  pagination.current = 1;
  await loadTableData();
  loading.value = false;
}

async function loadTableData() {
  const params: any = {
    // send pagination params so backend returns the requested page slice
    page: pagination.current,
    page_size: pagination.pageSize,
    currency: filters.currency,
    owners: filters.owners.includes(ALL_OWNERS_VALUE) ? [] : filters.owners,
    msku: filters.msku,
    rule: filters.rule,
  };
  // 仅在用户显式选择店铺时才传 shops 参数；未选择则不传（后端将按缓存 key 处理）
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
    // 后端返回的是已完成筛选的结果（后端也会根据 rule 做处理），前端可做额外展示/预览处理
    const fullList = res.list || [];
    // 后端可能返回 sync_time，记录用于展示（若为空则保留先前值）
    syncTime.value = res.sync_time || syncTime.value || null;

    const hasBackendList = Array.isArray(fullList) && fullList.length > 0;

    if (hasBackendList) {
      // 优先使用后端返回的列表（后端在 syncing 时会返回缓存数据）
      pagination.total = res.total || fullList.length;
      const previewed = applyFrontendRule(fullList, params.rule);
      tableData.value = (previewed || []).map((it: any) => mapItemToRow(it));
    } else {
      // 无论是否正在同步，只要后端未返回列表，则显示“暂无数据”（清空表格）
      tableData.value = [];
      pagination.total = res.total || 0;
    }

    // 处理同步状态与轮询
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

function formatPercent(v: any) {
  try {
    const n = parseFloat(v);
    if (isNaN(n)) return "-";
    return `${(n * 100).toFixed(2)}%`;
  } catch {
    return "-";
  }
}

// 复制到剪贴板（优先使用 navigator.clipboard）
async function copyToClipboard(text: string) {
  try {
    if (text == null || text === "") {
      ElMessage.warning("无内容可复制");
      return;
    }
    const s = String(text);
    if (navigator && (navigator as any).clipboard && (navigator as any).clipboard.writeText) {
      await (navigator as any).clipboard.writeText(s);
    } else {
      const ta = document.createElement("textarea");
      ta.value = s;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
      } catch {
        /* ignore */
      }
      document.body.removeChild(ta);
    }
    ElMessage.success("已复制");
  } catch (e) {
    console.error("copy failed", e);
    ElMessage.error("复制失败");
  }
}

// 双击拷贝入口（供模板使用）
function copyOnDblClick(text: string) {
  // 复用已有的复制函数，确保消息提示一致
  // 不使用 await，以免阻塞 UI；copyToClipboard 内部已处理异常与提示

  copyToClipboard(text);
}

/* onSearch removed (not used) */

function handleReset() {
  queryFormRef.value?.resetFields?.();
  filters.msku = "";
  filters.orderDateRange = [];
  // 其他字段重置
  filters.shops = [];
  filters.currency = "EUR";
  filters.owners = [];
  filters.rule = "rule1";
  handleQuery();
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

/* toggleSelectAllShops removed (not used) */
</script>

<style scoped lang="scss">
.page-container {
  padding: 16px;
}
.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.mt-4 {
  margin-top: 16px;
}
.table-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

/* 从 listing 复制的搜索栏与表格样式，保持一致性 */
.search-container {
  --el-font-size-base: 12px;
}
.search-container :deep(.el-form--inline .el-form-item) {
  margin-right: 20px;
  margin-left: 10px;
}
.search-container :deep(.search-row .ml-2) {
  margin-left: 8px;
}
.search-container :deep(.label-xs .el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
}
.search-container :deep(.el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
}

:deep(.el-table__header th) {
  text-align: center;
}
:deep(.el-table__header th .cell) {
  display: block;
  width: 100%;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.data-table {
  margin-top: 16px;
}
.data-table__toolbar {
  display: flex;
  justify-content: space-between;
  padding-bottom: 8px;
}
.data-table__toolbar--actions {
  display: flex;
  gap: 8px;
}
.data-table__toolbar--meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #666;
}
.data-table__toolbar--meta .sync-time {
  font-size: 11px;
  font-style: italic;
}
.data-table__toolbar--meta .sync-last {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #999;
}
.flex-x-end {
  display: flex;
  justify-content: flex-end;
}

/* visual tweaks requested */
.data-table__content :deep(.el-table__cell) {
  height: 48px;
  padding: 0 12px;
  font-size: 12px;
  line-height: 48px;
}

.two-line-cell {
  display: block;
}
.two-line-cell .line1,
.two-line-cell .line2 {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.two-line-cell .line1 {
  font-weight: 500;
}
.two-line-cell .line2 {
  font-size: 12px;
  color: #666;
}

.multiline > div {
  display: block;
}
.multiline > div > .two-line-cell {
  max-width: 100%;
}

/* center columns */
.col-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* MSKU single-line ellipsis */
.msku-cell {
  display: block;
}
.msku-item {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-wrap {
  display: inline-flex;
  gap: 0;
  align-items: center;
}
.copy-wrap .text {
  display: inline-block;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  -webkit-user-select: text;
  user-select: text;
}
.copy-icon {
  visibility: hidden;
  font-size: 12px;
  cursor: pointer;
}
.copy-wrap:hover .copy-icon {
  visibility: visible;
}

/* 重置表格内的 span 默认样式，避免浏览器或框架的内置样式影响对齐和行高 */
.data-table__content :deep(span) {
  padding: 0;
  margin: 0;
  font: inherit;
  line-height: normal;
  vertical-align: middle;
  color: inherit;
  background: transparent;
  border: 0;
}

/* popover multiline textarea tweaks */
.popover-advanced-input .el-input__inner[type="textarea"] {
  min-height: 88px;
  resize: none;
}
.popover-advanced-input .popover-body {
  padding: 6px;
}
.popover-advanced-input .popover-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
/* make the popover action buttons slightly smaller */
.popover-advanced-input .el-button {
  min-height: 26px;
  padding: 4px 8px;
  font-size: 11px;
}
.popover-advanced-input .el-button--mini {
  min-height: 24px;
  padding: 2px 6px;
}
/* make buttons have a square-ish frame with small radius (override is-round) */
.popover-advanced-input .el-button,
.popover-advanced-input .el-button.is-round,
.popover-advanced-input .el-button--mini.is-round {
  border-radius: 6px !important;
}

/* 可交互文本样式 removed to satisfy linting */

/* small question mark help icon next to rule select */
.rule-help {
  display: inline-block;
  width: 18px;
  height: 18px;
  font-size: 12px;
  line-height: 18px;
  color: #fff;
  text-align: center;
  cursor: help;
  background: #888;
  border-radius: 50%;
}

/* inline small spinner used for syncing status to avoid dependency on icon fonts */
.sync-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-left: 8px;
  vertical-align: middle;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-top-color: #409eff; /* element primary blue */
  border-radius: 50%;
  animation: sync-spin 0.9s linear infinite;
}

@keyframes sync-spin {
  to {
    transform: rotate(360deg);
  }
}

/* MSKU text highlight styles for matched rules */
:deep(.msku-rule2) {
  font-weight: 600;
  color: #d9302a !important;
}
:deep(.msku-rule3) {
  font-weight: 600;
  color: #138000 !important;
}
:deep(.msku-rule4) {
  font-weight: 600;
  color: #b8860b !important;
}
</style>
