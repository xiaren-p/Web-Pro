<template>
  <div class="charts-indicators-panel">
    <ul class="charts-slected-list" style="padding: 0px 20px 8px">
      <li
        v-for="item in topIndicators"
        :key="item.key"
        class="metric-card"
        :class="`card-${item.key}`"
        :data-type="item.type"
      >
        <button class="metric-close" title="移除" @click.stop="removeTop(item)">×</button>
        <div class="metric-inner">
          <div class="metric-content">
            <p class="metric-label">{{ item.label }}</p>
            <p class="metric-value">{{ item.value }}</p>
          </div>
        </div>
      </li>

      <li class="add-indicators" :class="{ expanded }" @click="addClicked">
        <template v-if="!expanded">+ 添加指标</template>
        <template v-else>收起指标</template>
      </li>
    </ul>

    <transition name="fade">
      <div v-show="expanded" class="indicators-list-con">
        <ul class="indicators-list">
          <li
            v-for="m in allDisplayIndicators"
            :key="m.key"
            class="indicator-card"
            :class="{ 'is-disabled': isTopIndicator(m) }"
            @click="handleCardClick(m)"
          >
            <div class="indicator-card-inner">
              <div class="indicator-label">{{ m.label }}</div>
              <div class="indicator-value">{{ m.value }}</div>
            </div>
          </li>
        </ul>
      </div>
    </transition>

    <el-dialog v-model:visible="showAddDialog" title="添加指标" width="720px">
      <el-input
        v-model="searchTerm"
        placeholder="搜索指标名称或关键字"
        clearable
        class="dialog-search"
      />
      <div style="padding: 8px 0">
        <el-checkbox-group v-model="selectedKeys">
          <div class="add-grid">
            <div v-for="opt in filteredOtherIndicators" :key="opt.key" class="add-item">
              <el-checkbox :label="opt.key">
                <div class="add-item-label">
                  <div class="add-item-name">{{ opt.label }}</div>
                  <div class="add-item-value">{{ opt.value }}</div>
                </div>
              </el-checkbox>
            </div>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedKeys.length" @click="confirmAdd">
          添加并应用
        </el-button>
      </template>
    </el-dialog>

    <!-- charts placeholder removed per request -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";

const expanded = ref(false);

const topIndicators = ref([
  { key: "clicks", label: "点击（总和）", value: "4394" },
  { key: "spends", label: "花费（总和）", value: "$594.1", type: 0 },
  { key: "sales", label: "广告销售额（总和）", value: "$1563.72" },
  { key: "acos", label: "ACoS（平均）", value: "37.99%", type: 1 },
]);

const otherIndicators = ref([
  { key: "impressions", label: "曝光量（总和）", value: "726095" },
  { key: "view_impressions", label: "可见次数（总和）", value: "0" },
  { key: "vcpm", label: "vCPM（平均）", value: "0" },
  { key: "ctr", label: "CTR（平均）", value: "0.61%" },
  { key: "cpc", label: "CPC（平均）", value: "$0.14" },
  { key: "direct_sales", label: "直接销售额（总和）", value: "$622.72" },
  { key: "indirect_sales", label: "间接销售额（总和）", value: "$941" },
  { key: "roas", label: "ROAS（总和）", value: "2.63" },
  { key: "orders", label: "广告订单（总和）", value: "112" },
  { key: "direct_orders", label: "直接订单（总和）", value: "55" },
  { key: "indirect_orders", label: "间接订单（总和）", value: "57" },
  { key: "indirect_orders_of_orders_percent", label: "间接订单占比（总和）", value: "50.89%" },
  { key: "cpa", label: "CPA（平均）", value: "$5.3" },
  { key: "cvr", label: "CVR（平均）", value: "2.55%" },
  { key: "unit_price", label: "广告笔单价（平均）", value: "$13.96" },
  { key: "direct_unit_price", label: "直接笔单价（平均）", value: "$11.32" },
  { key: "indirect_unit_price", label: "间接笔单价（平均）", value: "$16.51" },
  { key: "ad_units", label: "广告销量（总和）", value: "116" },
  { key: "direct_units", label: "直接销量（总和）", value: "58" },
  { key: "indirect_units", label: "间接销量（总和）", value: "58" },
  { key: "dpv", label: "DPV（总和）", value: "0" },
  { key: "video_5second_views", label: "5秒观看次数（总和）", value: "0" },
  { key: "video_5second_views_rate", label: "5秒观看率（平均）", value: "0%" },
  { key: "fist_quartile_views", label: "视频播1/4的次数（总和）", value: "0" },
  { key: "midpoint_views", label: "视频播一半的次数（总和）", value: "0" },
  { key: "third_quartile_views", label: "视频播3/4的次数（总和）", value: "0" },
  { key: "complete_views", label: "视频完播的次数（总和）", value: "0" },
  { key: "unmutes", label: "视频取消静音的次数（总和）", value: "0" },
  { key: "branded_search", label: "品牌搜索次数（总和）", value: "0" },
]);

const showAddDialog = ref(false);
const selectedKeys = ref<string[]>([]);
const searchTerm = ref("");

const filteredOtherIndicators = computed(() => {
  const q = searchTerm.value.trim().toLowerCase();
  if (!q) return otherIndicators.value;
  return otherIndicators.value.filter(
    (o: any) => o.label.toLowerCase().includes(q) || o.key.toLowerCase().includes(q)
  );
});

const allDisplayIndicators = computed(() => {
  return [...topIndicators.value, ...otherIndicators.value];
});

function isTopIndicator(item: any) {
  return topIndicators.value.some((t: any) => t.key === item.key);
}

function handleCardClick(item: any) {
  if (isTopIndicator(item)) return;
  promoteToTop(item);
}

function addClicked() {
  expanded.value = !expanded.value;
}

function promoteToTop(item: any) {
  // if exists in top -> move to front
  const idx = topIndicators.value.findIndex((t: any) => t.key === item.key);
  if (idx >= 0) {
    const [found] = topIndicators.value.splice(idx, 1);
    topIndicators.value.unshift(found);
    return;
  }
  // otherwise remove from other
  otherIndicators.value = otherIndicators.value.filter((o: any) => o.key !== item.key);
  // if top is full (4), move last one back to other
  if (topIndicators.value.length >= 4) {
    const moved = topIndicators.value.pop();
    if (moved) otherIndicators.value.unshift(moved);
  }
  // add new to front
  topIndicators.value.unshift(item);
}

function removeTop(item: any) {
  topIndicators.value = topIndicators.value.filter((t: any) => t.key !== item.key);
  // avoid duplicates in other
  if (!otherIndicators.value.find((o: any) => o.key === item.key))
    otherIndicators.value.unshift(item);
}

function confirmAdd() {
  if (!selectedKeys.value.length) return;
  // preserve selection order
  const toAdd = selectedKeys.value
    .map((k: string) => otherIndicators.value.find((o: any) => o.key === k))
    .filter(Boolean);
  for (const item of toAdd) {
    promoteToTop(item);
  }
  // remove added from otherIndicators
  const keys = new Set(selectedKeys.value);
  otherIndicators.value = otherIndicators.value.filter((o: any) => !keys.has(o.key));
  selectedKeys.value = [];
  showAddDialog.value = false;
  ElMessage.success("已添加指标");
}
</script>

<style scoped>
/* 简单的展开动画 */
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.charts-slected-list {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.charts-slected-list > li.metric-card {
  position: relative;
  display: flex;
  flex: 1 1 0;
  align-items: center;
  min-width: 160px;
  height: 76px;
  padding: 16px 20px 16px 24px;
  overflow: hidden;
  background: var(--surface-base);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
}

.metric-card::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 6px;
  content: "";
  background: linear-gradient(180deg, var(--color-primary-500) 0%, var(--color-primary-300) 100%);
  border-radius: var(--radius-xl) 0 0 var(--radius-xl);
}
.metric-card.card-acos::before {
  background: linear-gradient(180deg, var(--color-warning-500) 0%, var(--color-warning-300) 100%);
}
.metric-card.card-sales::before {
  background: linear-gradient(180deg, var(--color-success-500) 0%, var(--color-success-300) 100%);
}
.metric-card.card-spends::before {
  background: linear-gradient(180deg, var(--color-danger-500) 0%, var(--color-danger-300) 100%);
}
.metric-card.card-clicks::before {
  background: linear-gradient(180deg, var(--text-tertiary) 0%, var(--border-base) 100%);
}

.metric-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
}
.metric-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
  width: 100%;
}
.metric-label {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}
.metric-value {
  margin: 0;
  font-size: 26px;
  font-weight: bold;
  line-height: 1.2;
  color: var(--text-primary);
}

.metric-close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
  font-size: 16px;
  color: var(--text-tertiary);
  cursor: pointer;
  background: transparent;
  border: none;
  opacity: 0;
  transition: opacity 0.12s ease;
}
.metric-card:hover .metric-close {
  color: var(--color-danger-500);
  opacity: 1;
}

.add-indicators {
  display: flex;
  flex: 1 1 0;
  align-items: center;
  justify-content: center;
  min-width: 140px;
  height: 76px;
  padding: 10px;
  font-weight: 500;
  color: var(--color-primary-500);
  cursor: pointer;
  background: var(--surface-subtle);
  border: 1px dashed var(--color-primary-200);
  border-radius: var(--radius-xl);
  transition: all var(--transition-ui);
}
.add-indicators:hover {
  background: var(--surface-hover);
  border-color: var(--color-primary-500);
}
.add-indicators.expanded {
  background: var(--surface-hover);
  border-color: var(--color-primary-500);
}

.indicators-list-con {
  padding-bottom: 20px;
  margin-top: 8px;
}
.indicators-list {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  max-height: 480px;
  padding: 4px;
  padding-top: 16px;
  overflow: auto;
  border-top: 1px solid var(--border-subtle);
}
.indicators-list > li.indicator-card {
  padding: 14px 16px;
  cursor: pointer;
  background: var(--surface-base);
  border: 1px solid var(--border-base);
  border-radius: var(--radius-xl);
  transition:
    border-color var(--transition-ui),
    box-shadow var(--transition-ui);
}
.indicators-list > li.indicator-card:not(.is-disabled):hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}
.indicators-list > li.indicator-card.is-disabled {
  cursor: not-allowed;
  background: var(--surface-subtle);
  border-color: var(--border-base);
  box-shadow: none;
  opacity: 0.6;
}
.indicator-card-inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.indicator-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.indicator-value {
  margin-top: 2px;
  font-size: 22px;
  font-weight: bold;
  line-height: 1.1;
  color: var(--text-primary);
}

.add-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-height: 360px;
  overflow: auto;
}

.add-item {
  padding: 8px;
  background: var(--surface-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}
.add-item-label {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}
.add-item-name {
  font-size: 13px;
  color: var(--text-primary);
}
.add-item-value {
  font-size: 13px;
  color: var(--text-tertiary);
}

.dialog-search {
  margin-bottom: 8px;
}

@media (max-width: 900px) {
  .add-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 520px) {
  .add-grid {
    grid-template-columns: repeat(1, 1fr);
  }
  .charts-slected-list {
    flex-direction: column;
  }
  .metric-card {
    width: 100%;
    height: 72px;
  }
}
</style>
