<template>
  <div class="ad-groups-panel ads-detail-panel">
    <!-- 筛选栏（全部控件同一行，风格对齐广告活动页） -->
    <div class="filter-bar">
      <el-date-picker
        v-model="filters.range"
        size="small"
        class="filter-item date-picker"
        type="daterange"
        start-placeholder="开始"
        end-placeholder="结束"
        range-separator=" - "
        value-format="YYYY-MM-DD"
        style="width: 218px"
        unlink-panels
      />
      <el-select
        v-model="filters.state"
        size="small"
        class="filter-item w-110"
        placeholder="全部状态"
        clearable
      >
        <el-option label="已启用" value="enabled" />
        <el-option label="已暂停" value="paused" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item keyword-input"
        placeholder="请输入广告组"
        clearable
      />

      <!-- 筛选模板 / 查询 / 重置 -->
      <el-button size="small" :icon="Filter" class="btn-template">筛选模板</el-button>
      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>

      <!-- 占位：把列配置按鈔推到最右 -->
      <span style="flex: 1" />

      <!-- 列配置图标按鈔（右侧固定） -->
      <el-tooltip content="列配置" placement="top">
        <el-button
          text
          style="height: 32px; min-height: 32px; padding: 4px 9px; font-size: 16px; color: #606266"
          @click="columnConfigVisible = true"
        >
          <el-icon><Operation /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <!-- 表格 -->
    <div class="data-table-container">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        border
        :row-class-name="rowClassName"
        height="calc(100vh - 380px)"
        style="width: 100%"
        @selection-change="onSelectionChange"
        @header-dragend="onHeaderDragEnd"
      >
        <!-- 固定左侧：勾选列 -->
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :resizable="false"
          :selectable="(row: any) => !row._isSummary"
        />

        <!-- 固定左侧：有效 -->
        <el-table-column label="有效" width="80" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <el-switch
              v-if="!row._isSummary"
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
          </template>
        </el-table-column>

        <!-- 固定左侧：广告组（两行截断，悬浮复制） -->
        <el-table-column label="广告组" min-width="280" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <el-tooltip
              v-else
              :content="row.name ?? ''"
              placement="top"
              :show-after="400"
              :disabled="!isLikelyOverflow(row.name, 255)"
            >
              <div class="msku-cell">
                <span class="msku-text">{{ row.name || "-" }}</span>
                <el-icon class="copy-icon" @click.stop="copyText(row.name)">
                  <CopyDocument />
                </el-icon>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>

        <!-- 动态列（由 ColumnManager 控制 visible） -->
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="(col as any).minWidth || 120"
          align="center"
          :sortable="(col as any).sortable ?? false"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <template v-if="row._isSummary">---</template>
              <span
                v-else
                class="status-badge"
                :class="`status-${row.service_status_type || 'default'}`"
              >
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'default_bid'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="bid-cell">
                <span class="bid-icon">{{ currencyIcon }}</span>
                <el-input
                  v-model="row.default_bid"
                  size="small"
                  class="bid-input"
                  @change="onBidChange(row)"
                />
              </div>
            </template>
            <template v-else-if="col.prop === 'campaign_name'">
              <template v-if="row._isSummary">---</template>
              <el-tooltip
                v-else
                :content="row.campaign_name ?? ''"
                placement="top"
                :show-after="400"
                :disabled="!isLikelyOverflow(row.campaign_name, 205)"
              >
                <div class="msku-cell">
                  <span
                    class="campaign-state-icon"
                    :class="`state-${row.campaign_state || 'unknown'}`"
                  >
                    <template v-if="row.campaign_state === 'enabled'">
                      <span class="dot-circle" />
                    </template>
                    <template v-else-if="row.campaign_state === 'paused'">
                      <el-icon><VideoPause /></el-icon>
                    </template>
                    <template v-else-if="row.campaign_state === 'archived'">
                      <el-icon><CircleClose /></el-icon>
                    </template>
                  </span>
                  <span class="msku-text msku-text--dark">{{ row.campaign_name || "-" }}</span>
                  <el-icon class="copy-icon" @click.stop="copyText(row.campaign_name)">
                    <CopyDocument />
                  </el-icon>
                </div>
              </el-tooltip>
            </template>
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右侧：分析 -->
        <el-table-column label="分析" width="80" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button v-if="row.ad_group_id && !row._isSummary" type="primary" link size="small">
              分析
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页栏 -->
      <div class="pager-row">
        <span class="total-count">共 {{ total.toLocaleString() }} 条</span>
        <el-select
          v-model="pageSize"
          placeholder="每页"
          style="width: 100px"
          @change="onPageSizeChange"
        >
          <el-option label="25条/页" :value="25" />
          <el-option label="50条/页" :value="50" />
          <el-option label="100条/页" :value="100" />
          <el-option label="250条/页" :value="250" />
        </el-select>
        <el-pagination
          background
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, jumper"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 通用列配置抽屉 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { CopyDocument, Filter, Operation, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { getAdGroups } from "@/api/ads";

defineOptions({ name: "AdGroupsPanel" });

/**
 * 父页面透传过来的初始日期范围（路由 query 中的 date_start / date_end）。
 * 若存在则作为筛选栏的默认时间，用户可自行修改。
 *
 * @prop {string} campaignId - 广告活动 ID（必填，用于查询广告组）
 * @prop {string} profileId - 店铺 Profile ID（必填，用于数据隔离）
 * @prop {string[]} initialDateRange - 格式 ['YYYY-MM-DD', 'YYYY-MM-DD'] 或空数组
 */
const props = defineProps<{
  campaignId?: string;
  profileId?: string;
  initialDateRange?: string[];
}>();

/** 列可见性持久化（只存 prop → visible 映射，列定义结构始终以代码为准） */
const _savedColVis = useLocalStorage<Record<string, boolean>>("adgroups_panel_col_vis", {});

/** 筛选条件持久化（不含日期范围，日期由父组件 props 注入） */
const _savedFilters = useLocalStorage("adgroups_panel_filters", {
  state: "",
  keyword: "",
});

/** 筛选条件状态，range 以父页面传入的日期范围初始化 */
const filters = ref({
  range: (props.initialDateRange?.length === 2 ? [...props.initialDateRange] : []) as string[],
  state: _savedFilters.value.state,
  keyword: _savedFilters.value.keyword,
});

/** 列配置抽屉显示状态（持久化，刷新后保持上次开关状态） */
const columnConfigVisible = useLocalStorage<boolean>("adgroups_panel_drawer", false);

/** 数据加载状态 */
const loading = ref(false);

/** 分页状态（pageSize 持久化） */
const total = ref(0);
const currentPage = ref(1);
const pageSize = useLocalStorage<number>("adgroups_panel_page_size", 25);

/** 表格数据（后端返回的广告组列表） */
const tableData = ref<any[]>([]);

/** 汇总行数据（后端返回的 summary，挂载 _isSummary 标志后置顶） */
const summaryRow = ref<Record<string, unknown> | null>(null);

/** 货币符号（从接口响应中获取，用于默认竞价列前缀） */
const currencyIcon = ref<string>("$");

/**
 * 列定义（含 category，供 ColumnManager 分组展示）。
 * visible 控制是否在表格中渲染，由 ColumnManager @save 回调更新。
 */
const activeColumns = ref([
  // 设置
  { prop: "service_status", label: "服务状态", visible: true, category: "设置" },
  { prop: "portfolio_name", label: "广告组合", visible: true, category: "设置" },
  {
    prop: "campaign_name",
    label: "广告活动",
    visible: true,
    category: "设置",
    minWidth: 240,
    sortable: true,
  },
  { prop: "default_bid", label: "默认竞价", visible: true, category: "设置" },
  { prop: "product", label: "商品", visible: false, category: "设置" },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置" },
  // 转化
  { prop: "adsSales", label: "广告销售额", visible: true, category: "转化" },
  { prop: "adsSalesPercent", label: "广告销售额%", visible: true, category: "转化" },
  { prop: "directSales", label: "直接销售额", visible: false, category: "转化" },
  { prop: "acos", label: "ACoS", visible: true, category: "转化" },
  { prop: "roas", label: "ROAS", visible: true, category: "转化" },
  { prop: "adsOrders", label: "广告订单", visible: true, category: "转化" },
  { prop: "directOrders", label: "直接订单", visible: false, category: "转化" },
  { prop: "cvr", label: "CVR", visible: false, category: "转化" },
  { prop: "adsOrderPrice", label: "广告笔单价", visible: false, category: "转化" },
  { prop: "adsVolume", label: "广告销量", visible: false, category: "转化" },
  // 业绩
  { prop: "impressions", label: "曝光量", visible: true, category: "业绩" },
  { prop: "impressionsPercent", label: "曝光%", visible: false, category: "业绩" },
  { prop: "clicks", label: "点击", visible: true, category: "业绩" },
  { prop: "clicksPercent", label: "点击%", visible: false, category: "业绩" },
  { prop: "ctr", label: "CTR", visible: true, category: "业绩" },
  { prop: "cpc", label: "CPC", visible: true, category: "业绩" },
  { prop: "spends", label: "花费", visible: true, category: "业绩" },
  { prop: "spendsPercent", label: "花费%", visible: false, category: "业绩" },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩" },
]);

// 用存储的可见性覆盖默认定义（仅覆盖有记录的列，新列保留代码默认定义）
activeColumns.value.forEach((col) => {
  if (_savedColVis.value[col.prop] !== undefined) {
    col.visible = _savedColVis.value[col.prop];
  }
});

/**
 * 从所有列中过滤出 visible=true 的列，用于动态渲染表格列。
 *
 * @returns {当前需要展示的列定义数组}
 */
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

/**
 * 表格展示数据 = 汇总行（置顶）+ 分页数据列表。
 *
 * @returns {any[]} 拼接后的表格数据数组
 */
const displayData = computed<any[]>(() => {
  if (!summaryRow.value) return tableData.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...tableData.value];
});

/**
 * 表格行自定义类名，为汇总行附加样式类。
 *
 * @param {{ row: any }} 下构 - el-table 传入的行上下文
 * @returns {string} CSS 类名
 */
function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

/**
 * ColumnManager 保存回调，用新列配置替换 activeColumns。
 *
 * @param {typeof activeColumns.value} columns - 用户配置后的完整列数组
 */
function onColumnConfigSave(columns: typeof activeColumns.value): void {
  activeColumns.value = columns;
  _savedColVis.value = Object.fromEntries(columns.map((c) => [c.prop, c.visible]));
  ElMessage.success("列配置已保存");
}

// 筛选条件变化时自动持久化（不含日期范围）
watch([() => filters.value.state, () => filters.value.keyword], () => {
  _savedFilters.value = {
    state: filters.value.state,
    keyword: filters.value.keyword,
  };
});

/**
 * 触发搜索，重置到第一页后加载数据。
 */
function onSearch(): void {
  currentPage.value = 1;
  fetchData();
}

/**
 * 重置所有筛选条件并重新加载。
 */
function onReset(): void {
  filters.value.range = [];
  filters.value.state = "";
  filters.value.keyword = "";
  _savedFilters.value = { state: "", keyword: "" };
  currentPage.value = 1;
  fetchData();
}

/**
 * 页码变更时触发。
 *
 * @param {number} page - 新页码
 */
function onPageChange(page: number): void {
  currentPage.value = page;
  fetchData();
}

/**
 * 每页条数变更时触发。
 *
 * @param {number} size - 新的每页条数
 */
function onPageSizeChange(size: number): void {
  pageSize.value = size;
  currentPage.value = 1;
  fetchData();
}

/**
 * 加载广告组列表数据，调用后端 /ads/ad-groups 接口。
 * campaign_id / profile_id 由父页面通过 props 传入。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;

  loading.value = true;
  getAdGroups({
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    date_start: filters.value.range?.[0] || undefined,
    date_end: filters.value.range?.[1] || undefined,
    state: filters.value.state || undefined,
    keyword: filters.value.keyword || undefined,
    pageNum: currentPage.value,
    pageSize: pageSize.value,
  })
    .then((res) => {
      tableData.value = res.list ?? [];
      total.value = res.total ?? 0;
      summaryRow.value = res.summary ?? null;
      currencyIcon.value = res.currency_icon ?? "$";
    })
    .catch(() => {
      ElMessage.error("广告组数据加载失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

/**
 * 默认竞价修改占位处理（后端接口待实现）。
 * 当前仅本地更新 row.default_bid，不提交后端。
 *
 * @param {any} _row - 当前行数据对象，包含 ad_group_id 与最新 default_bid
 */
function onBidChange(row: any): void {
  // TODO(后端联调): 调用修改广告组默认竞价接口，提交 ad_group_id + default_bid
  void row;
}

/** 当前已勾选的广告组行 */
const selectedRows = ref<any[]>([]);

/**
 * 表格勾选变化回调。
 *
 * @param {any[]} rows - 当前所有已勾选的行数据
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

/**
 * 复制文本到剪贴板，成功后弹出提示。
 *
 * @param {string | undefined} text - 要复制的文本内容
 */
/**
 * 粗估文本是否会溢出指定显示宽度，用于按需启用 tooltip。
 * 以 9px/字符为均值（中文 ≈12px，英文 ≈7px），超出 maxLines 行则认为溢出。
 *
 * @param {string | null | undefined} text - 显示文本
 * @param {number} displayWidth - 可用文本宽度（px，已扣除 padding / 图标占用）
 * @param {number} maxLines - 最大行数，默认 2
 * @returns {boolean} 可能溢出返回 true
 */
function isLikelyOverflow(
  text: string | null | undefined,
  displayWidth: number,
  maxLines = 2
): boolean {
  if (!text) return false;
  const charsPerLine = Math.max(1, Math.floor(displayWidth / 9));
  return text.length > charsPerLine * maxLines;
}

async function copyText(text: string | undefined): Promise<void> {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败");
  }
}

/**
 * 列宽拖拽结束回调，强制列宽不低于各列的 minWidth。
 *
 * @param {number} newWidth - 拖拽后的新宽度
 * @param {number} _oldWidth - 拖拽前的旧宽度
 * @param {any} column - Element Plus 内部列对象（含 minWidth 属性）
 */
function onHeaderDragEnd(newWidth: number, _oldWidth: number, column: any): void {
  const minW = column.minWidth ? Number(column.minWidth) : 80;
  if (newWidth < minW) {
    column.width = minW;
    column.realWidth = minW;
  }
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
/* 通用筛选栏、表格、徽标、分页样式 → src/styles/ads-panel.scss → .ads-detail-panel */

/* keyword-input 宽度（广告组面板专属：180px） */
.keyword-input {
  flex: 0 0 180px;
  width: 180px;
}

/* 图标按钮（列配置触发器） */
.btn-icon-only {
  padding: 0 9px;
  color: var(--color-gray-600);
  border-color: var(--color-gray-300);
}

/* 单元格行高：广告组面板 9px 上下留白 */
:deep(.el-table .el-table__cell) {
  padding: 9px 0 !important;
}

/* 默认竞价可编辑小框 */
.bid-cell {
  display: inline-flex;
  gap: var(--spacing-1);
  align-items: center;
  width: 65px;

  .bid-icon {
    flex-shrink: 0;
    font-size: var(--font-size-xs);
    line-height: 1;
    color: var(--color-gray-600);
  }

  .bid-input {
    flex: 1;
    min-width: 0;

    :deep(.el-input__wrapper) {
      height: 26px;
      min-height: 26px;
      padding: 0 6px;
      border-radius: var(--radius-sm);
    }

    :deep(.el-input__inner) {
      height: 24px;
      font-size: var(--font-size-xs);
      text-align: right;
    }
  }
}
</style>
