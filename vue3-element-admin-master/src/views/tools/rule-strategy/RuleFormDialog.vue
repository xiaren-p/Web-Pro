<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑规则' : '创建规则'"
    width="960px"
    destroy-on-close
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px" class="rule-form">
      <el-divider content-position="left">基础信息</el-divider>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="规则名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入规则名称" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="规则状态">
            <el-switch
              v-model="form.status"
              active-value="active"
              inactive-value="inactive"
              active-text="启用"
              inactive-text="暂停"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="适用店铺" prop="shops">
        <el-select
          v-model="form.shops"
          multiple
          filterable
          style="width: 100%"
          placeholder="选择店铺"
          :filter-method="(v) => (shopSearch = v)"
          @change="(vals) => onSelectChange(vals, shopOptions, 'shops')"
        >
          <el-option
            :key="SELECT_ALL_MARKER"
            :label="'全选 / 取消全选'"
            :value="SELECT_ALL_MARKER"
          />
          <el-option
            v-for="opt in filteredShopOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <el-divider content-position="left">生效时间</el-divider>
      <el-form-item label="生效周期">
        <el-radio-group v-model="form.effectiveType" style="margin-bottom: 8px">
          <el-radio value="within_days">指定天数内</el-radio>
          <el-radio value="beyond_days">指定天数之外</el-radio>
          <el-radio value="date_range">日期范围</el-radio>
        </el-radio-group>

        <div
          v-if="form.effectiveType !== 'date_range'"
          style="display: flex; gap: 8px; align-items: center"
        >
          <span style="font-size: 13px; color: #606266">≤</span>
          <el-select v-model="form.effectiveDays" style="width: 120px" placeholder="选择天数">
            <el-option v-for="d in EFFECTIVE_DAYS" :key="d" :label="d + '天'" :value="d" />
          </el-select>
          <span style="font-size: 13px; color: #909399">
            {{ form.effectiveType === "beyond_days" ? "之外的广告实体" : "内的广告实体" }}
          </span>
        </div>

        <div v-else style="display: flex; gap: 8px; align-items: center">
          <el-select v-model="form.effectiveStart" placeholder="月" style="width: 80px" clearable>
            <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
          </el-select>
          <el-select v-model="form.effectiveEnd" placeholder="月" style="width: 80px" clearable>
            <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
          </el-select>
          <span style="font-size: 12px; color: #909399">（每年此时段生效）</span>
        </div>
      </el-form-item>

      <el-divider content-position="left">字段设置</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="归类">
            <div style="display: flex; gap: 8px; align-items: center">
              <el-checkbox v-model="form.unlimitedCategories" style="white-space: nowrap">
                不限
              </el-checkbox>
              <el-select
                v-model="form.categories"
                multiple
                filterable
                style="flex: 1"
                placeholder="选择归类"
                :disabled="form.unlimitedCategories"
                :filter-method="(v) => (assortSearch = v)"
                @change="(vals) => onSelectChange(vals, assortOptions, 'categories')"
              >
                <el-option
                  :key="SELECT_ALL_MARKER"
                  label="全选 / 取消全选"
                  :value="SELECT_ALL_MARKER"
                />
                <el-option
                  v-for="opt in assortOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </div>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="负责人">
            <div style="display: flex; gap: 8px; align-items: center">
              <el-checkbox v-model="form.unlimitedManagers" style="white-space: nowrap">
                不限
              </el-checkbox>
              <el-select
                v-model="form.managers"
                multiple
                filterable
                style="flex: 1"
                placeholder="选择负责人"
                :disabled="form.unlimitedManagers"
                :filter-method="(v) => (managerSearch = v)"
                @change="(vals) => onSelectChange(vals, managerOptions, 'managers')"
              >
                <el-option
                  :key="SELECT_ALL_MARKER"
                  label="全选 / 取消全选"
                  :value="SELECT_ALL_MARKER"
                />
                <el-option
                  v-for="opt in managerOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </div>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="标签">
            <div style="display: flex; gap: 8px; align-items: center">
              <el-checkbox v-model="form.unlimitedTags" style="white-space: nowrap">
                不限
              </el-checkbox>
              <el-select
                v-model="form.tags"
                multiple
                filterable
                style="flex: 1"
                placeholder="选择标签"
                :disabled="form.unlimitedTags"
                :filter-method="(v) => (labelSearch = v)"
                @change="(vals) => onSelectChange(vals, labelOptions, 'tags')"
              >
                <el-option
                  :key="SELECT_ALL_MARKER"
                  label="全选 / 取消全选"
                  :value="SELECT_ALL_MARKER"
                />
                <el-option
                  v-for="opt in labelOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </div>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">比对对象</el-divider>
      <el-form-item label="比对对象">
        <el-select v-model="form.comparisonTarget" style="width: 240px" placeholder="选择比对对象">
          <el-option
            v-for="opt in comparisonTargetOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <span style="margin-left: 8px; font-size: 12px; color: #909399">
          该规则将对此类广告实体生效
        </span>
      </el-form-item>

      <el-divider content-position="left">规则设置</el-divider>

      <el-form-item label="分时规则生效">
        <el-select
          v-model="form.linkedTimeRules"
          multiple
          clearable
          filterable
          style="width: 100%"
          placeholder="选择关联的分时规则（多选，非必选）"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <div style="margin-top: 2px; font-size: 11px; color: #c0c4cc">
          命中的分时规则不执行此广告规则（非必填）
        </div>
      </el-form-item>

      <el-form-item label="分时规则不生效">
        <el-select
          v-model="form.linkedTimeRulesExclude"
          multiple
          clearable
          filterable
          style="width: 100%"
          placeholder="选择排除的分时规则（多选，非必选）"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <div style="margin-top: 2px; font-size: 11px; color: #c0c4cc">
          命中的分时规则不执行此广告规则（非必填）
        </div>
      </el-form-item>

      <div class="condition-sets">
        <div v-for="(cSet, csIdx) in form.conditionSets" :key="csIdx" class="condition-set-card">
          <div class="condition-set-header">
            <span class="condition-set-label">条件组 {{ csIdx + 1 }}</span>
            <el-button
              v-if="form.conditionSets.length > 1"
              text
              type="danger"
              size="small"
              @click="removeConditionSet(csIdx)"
            >
              <el-icon><Delete /></el-icon>
              删除此组
            </el-button>
          </div>

          <div class="condition-set-days">
            <span style="font-size: 13px; color: #606266">≤</span>
            <el-select v-model="cSet.days" style="width: 110px" size="small" placeholder="天数">
              <el-option
                v-for="d in [7, 15, 30, 60, 90, 180, 365]"
                :key="d"
                :label="d + '天'"
                :value="d"
              />
            </el-select>
            <span style="font-size: 12px; color: #909399">内</span>
          </div>

          <div class="conditions-list">
            <div v-for="(cond, condIdx) in cSet.conditions" :key="condIdx" class="condition-row">
              <el-select
                v-model="cond.metric"
                style="width: 140px"
                size="small"
                placeholder="选择指标"
              >
                <el-option
                  v-for="m in metricOptions"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                />
              </el-select>
              <el-select v-model="cond.operator" style="width: 70px" size="small">
                <el-option
                  v-for="o in operatorOptions"
                  :key="o.value"
                  :label="o.label"
                  :value="o.value"
                />
              </el-select>
              <el-input-number
                v-model="cond.value"
                size="small"
                style="width: 130px"
                :min="0"
                :max="isPercentMetric(cond.metric) ? 9999 : 999999"
                :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                :precision="2"
              >
                <template v-if="isPercentMetric(cond.metric)" #suffix>
                  <span style="font-size: 12px; color: #909399">%</span>
                </template>
              </el-input-number>
              <el-button
                v-if="cSet.conditions.length > 1"
                text
                type="danger"
                size="small"
                @click="removeCondition(csIdx, condIdx)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>

          <el-button text type="primary" size="small" @click="addCondition(csIdx)">
            <el-icon><Plus /></el-icon>
            添加条件
          </el-button>
        </div>
      </div>

      <el-button type="primary" plain size="small" style="margin-top: 8px" @click="addConditionSet">
        <el-icon><Plus /></el-icon>
        新增条件组
      </el-button>

      <el-divider content-position="left">执行操作</el-divider>
      <el-form-item label="操作类型">
        <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center">
          <el-select v-model="form.actionType" style="width: 200px" placeholder="选择操作">
            <el-option
              v-for="opt in actionTypeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-input-number
            v-model="form.actionValue"
            style="width: 150px"
            :min="0"
            :max="form.actionType.includes('percent') ? 200 : 999999"
            :precision="2"
            :step="form.actionType.includes('percent') ? 1 : 0.1"
          />
          <span style="font-size: 13px; color: #909399">
            {{ form.actionType.includes("percent") ? "%" : "€" }}
          </span>
          <template v-if="form.actionType.includes('percent')">
            <span style="margin-left: 8px; font-size: 13px; color: #606266">
              {{ form.actionType.includes("decrease") ? "竞价不低于" : "竞价不高于" }}
            </span>
            <el-input-number
              v-model="form.actionLimit"
              style="width: 130px"
              :min="0"
              :max="200"
              :precision="2"
              :step="0.1"
            />
            <span style="font-size: 13px; color: #909399">€</span>
          </template>
        </div>
        <div style="margin-top: 4px; font-size: 12px; color: #c0c4cc">
          满足所有条件组时执行的操作
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">
        {{ isEdit ? "保存" : "创建" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * SP 广告规则草稿箱规则表单弹窗：创建 / 编辑一条广告自动规则。
 * 所属板块：tools / 广告规则策略 / 草稿箱。
 */
import type { RuleFormData } from "@/views/tools/rule-strategy/types";

import { ref, reactive, computed } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Delete } from "@element-plus/icons-vue";

import {
  getShopOptions,
  getManagerOptions,
  getAssortOptions,
  getLabelOptions,
  getTimePricingList,
} from "@/api/ads";

defineOptions({ name: "RuleFormDialog" });

// ── Props / Emits ──
const emit = defineEmits<{
  (e: "saved", data: RuleFormData): void;
}>();

// ── 常量 ──
const SELECT_ALL_MARKER = "__select_all__";
const EFFECTIVE_DAYS = [7, 15, 30, 60, 90, 180, 365];

// ── 表单初始值 ──
function createEmptyForm(): RuleFormData {
  return {
    id: "",
    name: "",
    shops: [],
    status: "active",
    effectiveType: "within_days",
    effectiveDays: 30,
    effectiveStart: "",
    effectiveEnd: "",
    categories: [],
    unlimitedCategories: false,
    managers: [],
    unlimitedManagers: false,
    tags: [],
    unlimitedTags: false,
    comparisonTarget: "keyword",
    conditionSets: [{ days: 30, conditions: [{ metric: "acos", operator: ">", value: 30 }] }],
    linkedTimeRules: [],
    linkedTimeRulesExclude: [],
    actionType: "bid_percent_decrease",
    actionValue: 0,
    actionLimit: null,
  };
}

const visible = ref(false);
const formRef = ref<any>(null);
const isEdit = ref(false);
const saving = ref(false);
const form = reactive<RuleFormData>(createEmptyForm());

const shopOptions = ref<{ value: number | string; label: string }[]>([]);
const managerOptions = ref<{ value: number | string; label: string }[]>([]);
const assortOptions = ref<{ value: string; label: string }[]>([]);
const labelOptions = ref<{ value: string; label: string }[]>([]);
const timeRuleOptions = ref<{ value: number | string; label: string }[]>([]);

const shopSearch = ref("");
const managerSearch = ref("");
const assortSearch = ref("");
const labelSearch = ref("");

const filteredShopOptions = computed(() =>
  !shopSearch.value
    ? shopOptions.value
    : shopOptions.value.filter((o) =>
        o.label.toLowerCase().includes(shopSearch.value.toLowerCase())
      )
);

const comparisonTargetOptions = [
  { value: "campaign", label: "广告活动" },
  { value: "ad_group", label: "广告组" },
  { value: "targeting", label: "定位组投放" },
  { value: "keyword", label: "关键词投放" },
  { value: "product_targeting", label: "商品投放" },
  { value: "search_terms", label: "用户搜索词" },
];

const metricOptions = [
  { value: "clicks", label: "点击" },
  { value: "orders", label: "订单" },
  { value: "impressions", label: "曝光" },
  { value: "adsVolume", label: "销量" },
  { value: "spend", label: "花费" },
  { value: "adsSales", label: "广告销售额" },
  { value: "cpc", label: "CPC" },
  { value: "cpa", label: "CPA" },
  { value: "acos", label: "ACoS(%)" },
  { value: "roas", label: "ROAS" },
  { value: "ctr", label: "CTR(%)" },
  { value: "cvr", label: "CVR(%)" },
  { value: "spendsPercent", label: "花费占比(%)" },
  { value: "adsSalesPercent", label: "销售额占比(%)" },
];

const operatorOptions = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: ">=", label: "≥" },
  { value: "<=", label: "≤" },
];

const actionTypeOptions = [
  { value: "bid_percent_decrease", label: "竞价按百分比降低" },
  { value: "bid_percent_increase", label: "竞价按百分比提高" },
  { value: "bid_fixed_decrease", label: "竞价按固定值减少" },
  { value: "bid_fixed_increase", label: "竞价按固定值增加" },
];

const formRules = {
  name: [{ required: true, message: "请输入规则名称", trigger: "blur" }],
  shops: [
    {
      validator: (_rule: any, value: any, cb: (msg?: Error) => void) => {
        if (!Array.isArray(value) || value.length === 0) {
          cb(new Error("请选择适用店铺"));
        } else {
          cb();
        }
      },
      trigger: "change",
    },
  ],
};

// ── 方法 ──
async function loadOptions(): Promise<void> {
  try {
    const [shops, managers, assorts, labels, timeRules] = await Promise.all([
      getShopOptions(),
      getManagerOptions(),
      getAssortOptions(),
      getLabelOptions(),
      getTimePricingList({ pageNum: 1, pageSize: 200 }),
    ]);
    shopOptions.value = (shops ?? []).map((o: any) => ({
      value: String(o.value ?? o.id),
      label: String(o.label ?? o.name ?? o.value),
    }));
    managerOptions.value = (managers ?? []).map((o: any) => ({
      value: String(o.value ?? o.id),
      label: String(o.label ?? o.name ?? o.value),
    }));
    assortOptions.value = (assorts ?? []).map((o: any) => ({
      value: String(o.value ?? o.id ?? o),
      label: String(o.label ?? o.name ?? o),
    }));
    labelOptions.value = (labels ?? []).map((o: any) => ({
      value: String(o.value ?? o.id ?? o),
      label: String(o.label ?? o.name ?? o),
    }));
    timeRuleOptions.value = (timeRules.list ?? []).map((tr: any) => ({
      value: tr.id,
      label: tr.name,
    }));
    if (!isEdit.value) {
      form.shops = shopOptions.value.map((o) => o.value);
    }
  } catch {
    // 选项加载失败不影响表单使用
  }
}

function onSelectChange(values: any[], options: any[], field: keyof RuleFormData): void {
  const markerIdx = values.indexOf(SELECT_ALL_MARKER);
  if (markerIdx === -1) return;
  const wasAllSelected = values.length - 1 >= options.length;
  (form as any)[field] = wasAllSelected ? [] : options.map((o: any) => o.value);
}

function isPercentMetric(metric: string): boolean {
  return ["acos", "ctr", "cvr", "spendsPercent", "adsSalesPercent"].includes(metric);
}

function addConditionSet(): void {
  form.conditionSets.push({ days: 30, conditions: [{ metric: "acos", operator: ">", value: 30 }] });
}

function removeConditionSet(idx: number): void {
  if (form.conditionSets.length <= 1) return;
  form.conditionSets.splice(idx, 1);
}

function addCondition(setIdx: number): void {
  form.conditionSets[setIdx].conditions.push({ metric: "clicks", operator: ">", value: 1 });
}

function removeCondition(setIdx: number, condIdx: number): void {
  const conds = form.conditionSets[setIdx].conditions;
  if (conds.length <= 1) return;
  conds.splice(condIdx, 1);
}

function open(data?: Partial<RuleFormData> | null): void {
  Object.assign(form, createEmptyForm());
  shopSearch.value = "";
  isEdit.value = false;
  if (data) {
    isEdit.value = true;
    Object.assign(form, JSON.parse(JSON.stringify(data)));
  }
  visible.value = true;
  loadOptions();
}

function handleClose(): void {
  visible.value = false;
}

async function handleSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    emit("saved", JSON.parse(JSON.stringify(form)));
    ElMessage.success(isEdit.value ? "规则已更新" : "规则已创建");
    visible.value = false;
  } finally {
    saving.value = false;
  }
}

defineExpose({ open });
</script>

<style scoped lang="scss">
.rule-form {
  max-height: 65vh;
  padding-right: 8px;
  overflow-y: auto;
}

.condition-sets {
  padding-left: 0;
  margin-top: 8px;
}

.condition-set-card {
  padding: 14px 16px;
  margin-bottom: 10px;
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.condition-set-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.condition-set-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.condition-set-days {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.condition-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
}
</style>
