<template>
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
      :data="data"
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
        <template #default="{ row }">{{ row.gross_margin_display || "-" }}</template>
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
        <template #default="{ row }">{{ row.net_gross_margin_display || "-" }}</template>
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
        <template #default="{ row }">{{ row.return_rate_display || "-" }}</template>
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
        <template #default="{ row }">{{ row.refund_amount_rate_display || "-" }}</template>
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
        <template #default="{ row }">{{ row.currency_icon || "" }}{{ row.spend || "-" }}</template>
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
        <template #default="{ row }">{{ row.spend_rate_display || "-" }}</template>
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
</template>

<script setup lang="ts">
/**
 * 亏损订单数据表格：纯展示组件，仅负责渲染表格列、同步状态条与分页器。
 * - 通过 props 接收 data / loading / pagination / syncing / syncTimeDisplay
 * - 通过 emit 把排序、分页变更回传父级 composable 处理
 * 所属板块：statistics / lossmakingOrders。
 */
import { ElMessage } from "element-plus";

interface Pagination {
  current: number;
  pageSize: number;
  total: number;
}

defineProps<{
  data: any[];
  loading: boolean;
  pagination: Pagination;
  syncing: boolean;
  syncTimeDisplay: string;
}>();

const emit = defineEmits<{
  (e: "sort-change", payload: { prop: string; order: string }): void;
  (e: "page-change", page: number): void;
  (e: "size-change", size: number): void;
}>();

/**
 * 双击复制单元格文本，优先使用现代 Clipboard API，降级到 textarea + execCommand。
 */
async function copyOnDblClick(text: string) {
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

function handleSortChange(payload: { prop: string; order: string }) {
  emit("sort-change", payload);
}

function onPageChange(page: number) {
  emit("page-change", page);
}

function onPageSizeChange(size: number) {
  emit("size-change", size);
}
</script>

<style scoped lang="scss">
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

.col-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

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

.sync-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-left: 8px;
  vertical-align: middle;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-top-color: #409eff;
  border-radius: 50%;
  animation: sync-spin 0.9s linear infinite;
}
@keyframes sync-spin {
  to {
    transform: rotate(360deg);
  }
}

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
