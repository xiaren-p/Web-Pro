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
/**
 * 广告指标展示组件：从汇总数据中读取真实值，支持用户自选 4 个置顶指标。
 */
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";

const props = defineProps<{
  summary: Record<string, unknown> | null;
}>();

/** 所有指标的定义：key 对应 summary 字段名，label 为中文标签 */
const METRIC_DEFS: { key: string; label: string }[] = [
  { key: "clicks", label: "点击（总和）" },
  { key: "spends", label: "花费（总和）" },
  { key: "adsSales", label: "广告销售额（总和）" },
  { key: "budget", label: "预算（总和）" },
  { key: "acos", label: "ACoS（平均）" },
  { key: "impressions", label: "曝光量（总和）" },
  { key: "ctr", label: "CTR（平均）" },
  { key: "cpc", label: "CPC（平均）" },
  { key: "cvr", label: "CVR（平均）" },
  { key: "roas", label: "ROAS（总和）" },
  { key: "directSales", label: "直接销售额（总和）" },
  { key: "indirectSales", label: "间接销售额（总和）" },
  { key: "adsOrders", label: "广告订单（总和）" },
  { key: "directOrders", label: "直接订单（总和）" },
  { key: "indirectOrders", label: "间接订单（总和）" },
  { key: "cpa", label: "CPA（平均）" },
  { key: "adsOrderPrice", label: "广告笔单价（平均）" },
  { key: "adsVolume", label: "广告销量（总和）" },
  { key: "impressionsPercent", label: "曝光占比（总和）" },
  { key: "clicksPercent", label: "点击占比（总和）" },
  { key: "spendsPercent", label: "花费占比（总和）" },
  { key: "adsSalesPercent", label: "广告销售额占比（总和）" },
  { key: "dpv", label: "DPV（总和）" },
  { key: "brandedSearch", label: "品牌搜索次数（总和）" },
];

/** 从 summary 中取字段值，null 兜底为 "-" */
function getMetricValue(key: string): string {
  if (!props.summary) return "-";
  const val = props.summary[key];
  if (val == null) return "-";
  return String(val);
}

/**
 * 根据 summary 动态计算所有指标的当前值。
 * 返回带 label/value 的完整对象，key 不变。
 */
const computedMetrics = computed(() => {
  return METRIC_DEFS.map((def) => ({
    key: def.key,
    label: def.label,
    value: getMetricValue(def.key),
  }));
});

const expanded = ref(false);
const showAddDialog = ref(false);
const selectedKeys = ref<string[]>([]);
const searchTerm = ref("");

/** 默认置顶 4 个核心指标 */
const DEFAULT_TOP_KEYS = ["clicks", "spends", "adsSales", "acos"];

/** 置顶指标 keys 的 localStorage 缓存键 */
const TOP_METRICS_KEY = "ADS_SP_TOP_METRICS_V1";

/**
 * 从 localStorage 读取置顶指标 keys，校验其对应的指标定义仍存在。
 *
 * @returns {string[] | null} 缓存的 keys；无缓存或全部失效时返回 null
 */
function readCachedTopKeys(): string[] | null {
  try {
    const raw = localStorage.getItem(TOP_METRICS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const validKeys = new Set(METRIC_DEFS.map((d) => d.key));
    const filtered = parsed.filter(
      (k: unknown) => typeof k === "string" && validKeys.has(k as string)
    );
    return filtered.length > 0 ? (filtered as string[]) : null;
  } catch {
    return null;
  }
}

/**
 * 持久化置顶指标 keys 到 localStorage。
 *
 * @param {string[]} keys - 当前置顶指标的 key 列表
 */
function persistTopKeys(keys: string[]): void {
  try {
    localStorage.setItem(TOP_METRICS_KEY, JSON.stringify(keys));
  } catch {
    // 容量满或隐私模式：静默忽略
  }
}

const topIndicators = ref<{ key: string; label: string; value: string; type?: number }[]>([]);
const otherIndicators = ref<{ key: string; label: string; value: string }[]>([]);

/**
 * 初始化时从 computedMetrics 中拆出 top 和 other 两部分。
 * 首次加载优先用 localStorage 缓存的置顶 keys，无缓存才用默认 4 个核心指标。
 * 每次 summary 变化时同步刷新数值而不重置用户选择。
 */
function syncMetricsFromSummary() {
  const all = computedMetrics.value;

  // 首次加载：优先用缓存 keys，回退默认置顶
  if (topIndicators.value.length === 0 && otherIndicators.value.length === 0) {
    const cachedKeys = readCachedTopKeys();
    const topKeys = cachedKeys ?? DEFAULT_TOP_KEYS;
    for (const m of all) {
      if (topKeys.includes(m.key)) {
        topIndicators.value.push({ ...m, type: m.key === "acos" ? 1 : 0 });
      } else {
        otherIndicators.value.push({ ...m });
      }
    }
    // 首次若用了缓存，需保证置顶顺序与缓存一致
    if (cachedKeys) {
      topIndicators.value.sort((a, b) => cachedKeys.indexOf(a.key) - cachedKeys.indexOf(b.key));
    }
    return;
  }

  // 已有选择的：只刷新值
  for (const m of all) {
    const topItem = topIndicators.value.find((t) => t.key === m.key);
    if (topItem) {
      topItem.value = m.value;
      continue;
    }
    const otherItem = otherIndicators.value.find((o) => o.key === m.key);
    if (otherItem) {
      otherItem.value = m.value;
    }
  }
}

watch(() => props.summary, syncMetricsFromSummary, { immediate: true });

const filteredOtherIndicators = computed(() => {
  const q = searchTerm.value.trim().toLowerCase();
  if (!q) return otherIndicators.value;
  return otherIndicators.value.filter(
    (o) => o.label.toLowerCase().includes(q) || o.key.toLowerCase().includes(q)
  );
});

const allDisplayIndicators = computed(() => {
  return [...topIndicators.value, ...otherIndicators.value];
});

function isTopIndicator(item: { key: string }) {
  return topIndicators.value.some((t) => t.key === item.key);
}

function handleCardClick(item: { key: string; label: string; value: string }) {
  if (isTopIndicator(item)) return;
  promoteToTop(item);
}

function addClicked() {
  expanded.value = !expanded.value;
}

function promoteToTop(item: { key: string; label: string; value: string }) {
  // 已在置顶则移到首位
  const idx = topIndicators.value.findIndex((t) => t.key === item.key);
  if (idx >= 0) {
    const [found] = topIndicators.value.splice(idx, 1);
    topIndicators.value.unshift(found);
    persistTopKeys(topIndicators.value.map((t) => t.key));
    return;
  }
  // 从 other 中移除
  otherIndicators.value = otherIndicators.value.filter((o) => o.key !== item.key);
  // 置顶最多 4 个
  if (topIndicators.value.length >= 4) {
    const moved = topIndicators.value.pop();
    if (moved) otherIndicators.value.unshift(moved);
  }
  topIndicators.value.unshift({ ...item });
  persistTopKeys(topIndicators.value.map((t) => t.key));
}

function removeTop(item: { key: string; label: string; value: string }) {
  topIndicators.value = topIndicators.value.filter((t) => t.key !== item.key);
  if (!otherIndicators.value.find((o) => o.key === item.key))
    otherIndicators.value.unshift({ ...item });
  persistTopKeys(topIndicators.value.map((t) => t.key));
}

function confirmAdd() {
  if (!selectedKeys.value.length) return;
  const toAdd = selectedKeys.value
    .map((k) => otherIndicators.value.find((o) => o.key === k))
    .filter(Boolean) as { key: string; label: string; value: string }[];
  for (const item of toAdd) {
    promoteToTop(item);
  }
  const keys = new Set(selectedKeys.value);
  otherIndicators.value = otherIndicators.value.filter((o) => !keys.has(o.key));
  selectedKeys.value = [];
  showAddDialog.value = false;
  // promoteToTop 内部已持久化，此处无需重复
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
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-start;
}
.charts-slected-list > li.metric-card {
  position: relative;
  display: flex;
  flex: 1 1 0;
  align-items: center;
  min-width: 120px;
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
  font-size: clamp(11px, 1.4vw, 14px);
  font-weight: 500;
  color: var(--text-secondary);
}
.metric-value {
  margin: 0;
  font-size: clamp(18px, 2.2vw, 26px);
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
  min-width: 100px;
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
