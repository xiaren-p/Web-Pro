<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑规则' : '创建规则'"
    width="1080px"
    destroy-on-close
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px" class="rule-form">
      <!-- ═══════════ 基础信息 ═══════════ -->
      <el-divider content-position="left">基础信息</el-divider>
      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="规则名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入规则名称" maxlength="100" clearable />
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
              inline-prompt
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
          placeholder="请选择适用店铺"
          popper-class="rule-select-popper"
          :filter-method="(v: string) => (shopSearch = v)"
          @change="(vals: any[]) => onSelectChange(vals, shopOptions, 'shops')"
        >
          <el-option :key="SELECT_ALL_MARKER" label="全选 / 取消全选" :value="SELECT_ALL_MARKER" />
          <el-option
            v-for="opt in filteredShopOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <!-- ═══════════ 生效时间 ═══════════ -->
      <el-divider content-position="left">生效时间</el-divider>
      <el-form-item label="生效周期">
        <el-radio-group v-model="form.effectiveType" class="mb-2">
          <el-radio-button value="within_days">指定天数内</el-radio-button>
          <el-radio-button value="beyond_days">指定天数之外</el-radio-button>
          <el-radio-button value="date_range">日期范围</el-radio-button>
        </el-radio-group>

        <div v-if="form.effectiveType !== 'date_range'" class="effective-days-row">
          <span class="effective-prefix">≤</span>
          <el-select
            v-model="form.effectiveDays"
            style="width: 140px"
            placeholder="选择或输入天数"
            filterable
            allow-create
            default-first-option
          >
            <el-option v-for="d in PRESET_DAYS" :key="d" :label="d + ' 天'" :value="d" />
          </el-select>
          <span class="effective-suffix">
            {{ form.effectiveType === "beyond_days" ? "之外的广告实体" : "内的广告实体" }}
          </span>
        </div>

        <div v-else class="effective-date-row">
          <el-select
            v-model="form.effectiveStart"
            placeholder="起始月"
            style="width: 90px"
            clearable
          >
            <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
          </el-select>
          <span class="date-sep">至</span>
          <el-select v-model="form.effectiveEnd" placeholder="结束月" style="width: 90px" clearable>
            <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
          </el-select>
          <span class="effective-date-hint">每年此时段生效</span>
        </div>
      </el-form-item>

      <!-- ═══════════ 字段设置 ═══════════ -->
      <el-divider content-position="left">字段设置</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="归类" class="field-setting-item">
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedCategories">不限</el-checkbox>
              <el-select
                v-model="form.categories"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                style="flex: 1"
                placeholder="选择归类"
                :disabled="form.unlimitedCategories"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, assortOptions, 'categories')"
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
          <el-form-item label="负责人" class="field-setting-item">
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedManagers">不限</el-checkbox>
              <el-select
                v-model="form.managers"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                style="flex: 1"
                placeholder="选择负责人"
                :disabled="form.unlimitedManagers"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, managerOptions, 'managers')"
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
          <el-form-item label="标签" class="field-setting-item">
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedTags">不限</el-checkbox>
              <el-select
                v-model="form.tags"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                style="flex: 1"
                placeholder="选择标签"
                :disabled="form.unlimitedTags"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, labelOptions, 'tags')"
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

      <!-- ═══════════ 比对对象 ═══════════ -->
      <el-divider content-position="left">比对对象</el-divider>
      <el-form-item label="比对对象">
        <div class="comparison-target-group">
          <!-- 多选组：定位组投放 / 关键词投放 / 商品投放 -->
          <el-checkbox-group v-model="form.comparisonMultiTargets" class="comparison-checkboxes">
            <el-checkbox v-for="opt in multiTargetOptions" :key="opt.value" :label="opt.value">
              {{ opt.label }}
            </el-checkbox>
          </el-checkbox-group>
          <span class="comparison-sep">|</span>
          <!-- 单选且禁用：广告活动 / 广告组 -->
          <el-radio-group
            v-model="form.comparisonTarget"
            class="comparison-radios"
            @change="onTargetChange"
          >
            <el-radio
              v-for="opt in singleTargetOptions"
              :key="opt.value"
              :label="opt.value"
              :disabled="opt.disabled"
            >
              {{ opt.label }}
            </el-radio>
            <el-radio value="search_terms">用户搜索词</el-radio>
          </el-radio-group>
        </div>
        <span class="form-hint">
          {{
            form.comparisonTarget === "search_terms"
              ? "用户搜索词仅可单选"
              : "定位组投放、关键词投放、商品投放可多选"
          }}
        </span>
      </el-form-item>

      <!-- ═══════════ 规则关系提示 ═══════════ -->
      <el-alert
        title="规则关系说明"
        type="info"
        :closable="false"
        show-icon
        class="rule-relation-alert"
      >
        <template #default>
          <p>
            条件组之间为
            <b>或</b>
            关系（第一个条件组未命中则比对下一个，最终只匹配一个），组内条件为
            <b>并</b>
            关系（全部满足才触发）。
          </p>
        </template>
      </el-alert>

      <!-- ═══════════ 规则设置（条件组）══ -->
      <el-divider content-position="left">规则设置</el-divider>

      <el-form-item label="分时规则生效">
        <el-select
          v-model="form.linkedTimeRules"
          multiple
          clearable
          filterable
          collapse-tags
          collapse-tags-tooltip
          style="width: 100%"
          placeholder="选择关联的分时规则（多选，非必选）"
          popper-class="rule-select-popper"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <div class="form-hint">命中的分时规则不执行此广告规则</div>
      </el-form-item>

      <el-form-item label="分时规则不生效">
        <el-select
          v-model="form.linkedTimeRulesExclude"
          multiple
          clearable
          filterable
          collapse-tags
          collapse-tags-tooltip
          style="width: 100%"
          placeholder="选择排除的分时规则（多选，非必选）"
          popper-class="rule-select-popper"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <div class="form-hint">命中的分时规则不执行此广告规则</div>
      </el-form-item>

      <!-- 条件组 -->
      <div class="condition-sets">
        <div v-for="(cSet, csIdx) in form.conditionSets" :key="csIdx" class="condition-set-card">
          <div class="condition-set-header">
            <span class="condition-set-label">条件组 {{ csIdx + 1 }}</span>
            <el-tag v-if="form.conditionSets.length > 1" type="info" size="small" effect="plain">
              {{ csIdx === 0 ? "优先匹配" : "备选" }}
            </el-tag>
            <el-button
              v-if="form.conditionSets.length > 1"
              text
              type="danger"
              size="small"
              @click="removeConditionSet(csIdx)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>

          <div class="condition-set-days">
            <span class="days-prefix">≤</span>
            <el-select
              v-model="cSet.days"
              style="width: 140px"
              size="small"
              placeholder="选择或输入天数"
              filterable
              allow-create
              default-first-option
            >
              <el-option v-for="d in PRESET_DAYS" :key="d" :label="d + ' 天'" :value="d" />
            </el-select>
            <span class="days-suffix">内</span>
            <el-tag size="small" type="primary" effect="plain" style="margin-left: 8px">
              全部满足才触发
            </el-tag>
          </div>

          <div class="conditions-list">
            <div v-for="(cond, condIdx) in cSet.conditions" :key="condIdx" class="condition-row">
              <el-select
                v-model="cond.metric"
                style="width: 150px"
                size="small"
                placeholder="指标"
                popper-class="rule-select-popper"
                @change="
                  cond.operator = '>';
                  cond.value2 = undefined;
                "
              >
                <el-option
                  v-for="m in metricOptions"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                />
              </el-select>

              <template v-if="cond.isRange">
                <span class="range-placeholder">值</span>
                <el-select
                  v-model="cond.operator"
                  style="width: 72px"
                  size="small"
                  popper-class="rule-select-popper"
                >
                  <el-option
                    v-for="o in operatorOptions"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
                <span class="range-var">{{ cond.metric }}</span>
                <el-select
                  v-model="cond.operator2"
                  style="width: 72px"
                  size="small"
                  popper-class="rule-select-popper"
                >
                  <el-option
                    v-for="o in operatorOptions"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
                <el-input-number
                  v-model="cond.value2"
                  size="small"
                  style="width: 120px"
                  :min="0"
                  :max="999999"
                  :precision="2"
                  :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                  controls-position="right"
                >
                  <template v-if="isPercentMetric(cond.metric)" #suffix>
                    <span class="input-suffix">%</span>
                  </template>
                </el-input-number>
              </template>

              <template v-else>
                <el-select
                  v-model="cond.operator"
                  style="width: 72px"
                  size="small"
                  popper-class="rule-select-popper"
                >
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
                  style="width: 140px"
                  :min="0"
                  :max="999999"
                  :precision="2"
                  :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                  controls-position="right"
                >
                  <template v-if="isPercentMetric(cond.metric)" #suffix>
                    <span class="input-suffix">%</span>
                  </template>
                </el-input-number>
              </template>

              <el-button
                text
                type="primary"
                size="small"
                class="cond-toggle-btn"
                @click="toggleConditionRange(cSet, condIdx)"
              >
                {{ cond.isRange ? "切为两段" : "切为范围" }}
              </el-button>

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

            <el-alert
              v-if="getConditionConflict(cSet)"
              :title="getConditionConflict(cSet) ?? ''"
              type="error"
              :closable="false"
              show-icon
              class="conflict-alert"
            />
          </div>

          <el-button text type="primary" size="small" @click="addCondition(csIdx)">
            <el-icon><Plus /></el-icon>
            添加条件
          </el-button>
        </div>
      </div>

      <el-button type="primary" plain size="small" class="add-set-btn" @click="addConditionSet">
        <el-icon><Plus /></el-icon>
        新增条件组
      </el-button>

      <!-- ═══════════ 执行操作 ═══════════ -->
      <el-divider content-position="left">执行操作</el-divider>

      <!-- ── 搜索词专属 ── -->
      <template v-if="form.comparisonTarget === 'search_terms'">
        <el-form-item label="否定操作">
          <el-select
            v-model="form.negativeAction"
            style="width: 240px"
            placeholder="选择否定操作（可选）"
            clearable
          >
            <el-option
              v-for="opt in negativeActionOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <span class="form-hint">对匹配的用户搜索词添加否定关键词，可不选</span>
        </el-form-item>

        <el-form-item label="关键词投放">
          <el-select
            v-model="form.addKeywordAction"
            style="width: 320px"
            placeholder="添加关键词到手动广告活动（可选）"
            clearable
            popper-class="rule-select-popper"
          >
            <el-option
              v-for="opt in addKeywordActionOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <span class="form-hint">可不选，也可和否定操作同时调整</span>

          <div v-if="form.addKeywordAction" class="keyword-add-panel">
            <div class="kadd-row">
              <span class="kadd-label">匹配方式</span>
              <el-select v-model="form.addKeywordMatchType" style="width: 140px" size="small">
                <el-option label="广泛匹配" value="broad" />
                <el-option label="词组匹配" value="phrase" />
                <el-option label="精准匹配" value="exact" />
              </el-select>
            </div>
            <div class="kadd-row">
              <span class="kadd-label">竞价方式</span>
              <el-radio-group v-model="form.addKeywordBidType" size="small">
                <el-radio-button value="actual_cpc">采用实际出单 CPC</el-radio-button>
                <el-radio-button value="fixed">填写固定值</el-radio-button>
              </el-radio-group>
            </div>
            <div v-if="form.addKeywordBidType === 'actual_cpc'" class="kadd-row">
              <span class="kadd-label">最高竞价</span>
              <el-input-number
                v-model="form.addKeywordMaxBid"
                size="small"
                style="width: 130px"
                :min="0"
                :step="0.01"
                :precision="2"
                controls-position="right"
              />
              <span class="action-unit">€</span>
            </div>
            <div v-else class="kadd-row">
              <span class="kadd-label">固定竞价</span>
              <el-input-number
                v-model="form.addKeywordFixedBid"
                size="small"
                style="width: 130px"
                :min="0"
                :step="0.01"
                :precision="2"
                controls-position="right"
              />
              <span class="action-unit">€</span>
            </div>
          </div>

          <el-alert
            v-if="form.addKeywordAction"
            title="关键词投放说明"
            type="info"
            :closable="false"
            show-icon
            class="keyword-add-note"
          >
            <template #default>
              <p>
                若广告活动为
                <b>手动广告</b>
                ，直接在该活动中添加关键词；若为
                <b>自动广告</b>
                ，则在同店铺同站点下查找同名手动广告活动添加关键词。
              </p>
            </template>
          </el-alert>
        </el-form-item>
      </template>

      <!-- ── 通用：竞价操作 + 预算操作（可并存）── -->
      <template v-else>
        <el-alert
          title="提示：竞价操作和预算操作可同时添加，互不影响"
          type="success"
          :closable="false"
          show-icon
          class="mb-4"
        />

        <!-- 竞价操作列表 -->
        <el-form-item label="竞价操作">
          <div class="action-list">
            <div v-for="(act, idx) in form.bidActions" :key="idx" class="action-item">
              <el-select
                v-model="act.type"
                style="width: 200px"
                placeholder="选择操作"
                popper-class="rule-select-popper"
              >
                <el-option
                  v-for="opt in bidActionOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>

              <template v-if="isBidValueAction(act.type)">
                <el-input-number
                  v-model="act.value"
                  style="width: 140px"
                  :min="0"
                  :precision="2"
                  :max="act.type.includes('percent') ? 200 : 999999"
                  :step="act.type.includes('percent') ? 1 : 0.1"
                  controls-position="right"
                />
                <span class="action-unit">{{ act.type.includes("percent") ? "%" : "€" }}</span>
              </template>

              <!-- 提高：最高不超过 -->
              <template v-if="isIncreaseType(act.type)">
                <span class="action-limit-label">最高不超过</span>
                <el-input-number
                  v-model="act.limit"
                  style="width: 130px"
                  :min="0"
                  :precision="2"
                  :step="0.1"
                  controls-position="right"
                />
                <span class="action-unit">€</span>
              </template>

              <!-- 降低（固定值）：最低不低于 -->
              <template v-if="act.type === 'bid_fixed_decrease'">
                <span class="action-limit-label">最低不低于</span>
                <el-input-number
                  v-model="act.limit"
                  style="width: 130px"
                  :min="0"
                  :precision="2"
                  :step="0.1"
                  controls-position="right"
                />
                <span class="action-unit">€</span>
              </template>

              <el-button
                v-if="form.bidActions.length > 1"
                text
                type="danger"
                size="small"
                @click="form.bidActions.splice(idx, 1)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-button text type="primary" size="small" class="add-action-btn" @click="addBidAction">
            <el-icon><Plus /></el-icon>
            添加竞价操作
          </el-button>
        </el-form-item>

        <!-- 预算操作列表 -->
        <el-form-item label="预算操作">
          <div class="action-list">
            <div v-for="(act, idx) in form.budgetActions" :key="idx" class="action-item">
              <el-select
                v-model="act.type"
                style="width: 200px"
                placeholder="选择操作"
                popper-class="rule-select-popper"
              >
                <el-option
                  v-for="opt in budgetActionOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>

              <template v-if="act.type !== 'no_adjust'">
                <el-input-number
                  v-model="act.value"
                  style="width: 130px"
                  :min="1"
                  :step="1"
                  :precision="0"
                  controls-position="right"
                />
                <span class="action-unit">€/天</span>
                <span class="action-limit-label">不超过</span>
                <el-input-number
                  v-model="act.limit"
                  style="width: 130px"
                  :min="0"
                  :precision="2"
                  :step="0.1"
                  controls-position="right"
                />
                <span class="action-unit">€/天</span>
              </template>

              <el-button
                v-if="form.budgetActions.length > 1"
                text
                type="danger"
                size="small"
                @click="form.budgetActions.splice(idx, 1)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-button
            text
            type="primary"
            size="small"
            class="add-action-btn"
            @click="addBudgetAction"
          >
            <el-icon><Plus /></el-icon>
            添加预算操作
          </el-button>
        </el-form-item>
      </template>
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
 * SP 广告规则草稿箱规则表单弹窗。
 * 所属板块：tools / 广告规则策略 / 草稿箱。
 */
import type { RuleFormData, ConditionWithRange } from "@/views/tools/rule-strategy//types";

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

const emit = defineEmits<{ (e: "saved", data: RuleFormData): void }>();

const SELECT_ALL_MARKER = "__select_all__";
const PRESET_DAYS = [7, 14, 15, 21, 30, 45, 60, 90, 180, 365];
const shopSearch = ref("");

// ── 表单 ──
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
    comparisonTarget: "",
    comparisonMultiTargets: [],
    conditionSets: [{ days: 30, conditions: [{ metric: "acos", operator: ">", value: 30 }] }],
    linkedTimeRules: [],
    linkedTimeRulesExclude: [],
    negativeAction: "",
    addKeywordAction: "",
    addKeywordMatchType: "broad",
    addKeywordBidType: "actual_cpc",
    addKeywordMaxBid: 0.2,
    addKeywordFixedBid: null,
    bidActions: [{ type: "bid_percent_decrease", value: 0, limit: null }],
    budgetActions: [{ type: "budget_increase", value: 0, limit: null }],
  };
}

const visible = ref(false);
const formRef = ref<any>(null);
const isEdit = ref(false);
const saving = ref(false);
const form = reactive<RuleFormData>(createEmptyForm());

// ── 下拉选项 ──
const shopOptions = ref<{ value: any; label: string }[]>([]);
const managerOptions = ref<{ value: any; label: string }[]>([]);
const assortOptions = ref<{ value: string; label: string }[]>([]);
const labelOptions = ref<{ value: string; label: string }[]>([]);
const timeRuleOptions = ref<{ value: any; label: string }[]>([]);
const filteredShopOptions = computed(() =>
  !shopSearch.value
    ? shopOptions.value
    : shopOptions.value.filter((o) =>
        o.label.toLowerCase().includes(shopSearch.value.toLowerCase())
      )
);

// ── 比对对象选项 ──
const multiTargetOptions = [
  { value: "targeting", label: "定位组投放" },
  { value: "keyword", label: "关键词投放" },
  { value: "product_targeting", label: "商品投放" },
];
const singleTargetOptions = [
  { value: "campaign", label: "广告活动", disabled: true },
  { value: "ad_group", label: "广告组", disabled: true },
];

// ── 指标 / 操作符 ──
const metricOptions = [
  { value: "clicks", label: "点击" },
  { value: "orders", label: "订单" },
  { value: "impressions", label: "曝光" },
  { value: "adsVolume", label: "销量" },
  { value: "spend", label: "花费" },
  { value: "adsSales", label: "广告销售额" },
  { value: "cpc", label: "CPC" },
  { value: "cpa", label: "CPA" },
  { value: "acos", label: "ACoS (%)" },
  { value: "roas", label: "ROAS" },
  { value: "ctr", label: "CTR (%)" },
  { value: "cvr", label: "CVR (%)" },
  { value: "spendsPercent", label: "花费占比 (%)" },
  { value: "adsSalesPercent", label: "销售额占比 (%)" },
];
const operatorOptions = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: ">=", label: "≥" },
  { value: "<=", label: "≤" },
];

// ── 竞价操作（不含预算）──
const bidActionOptions = [
  { value: "bid_percent_increase", label: "竞价按百分比提高" },
  { value: "bid_fixed_increase", label: "竞价按固定值增加" },
  { value: "bid_percent_decrease", label: "竞价按百分比降低" },
  { value: "bid_fixed_decrease", label: "竞价按固定值减少" },
  { value: "no_adjust", label: "不调整" },
  { value: "pause", label: "暂停" },
  { value: "archive", label: "归档" },
];
const budgetActionOptions = [
  { value: "budget_increase", label: "广告活动预算增加" },
  { value: "budget_decrease", label: "广告活动预算减少" },
  { value: "no_adjust", label: "不调整" },
];
const negativeActionOptions = [
  { value: "negative_exact", label: "添加精准否定关键词" },
  { value: "negative_phrase", label: "添加否定词组" },
];
const addKeywordActionOptions = [{ value: "add_keyword", label: "添加对应手动广告活动关键词" }];

function isBidValueAction(t: string): boolean {
  return t.startsWith("bid_percent_") || t.startsWith("bid_fixed_");
}
function isIncreaseType(t: string): boolean {
  return t.includes("increase");
}

// ── 目标切换 ──
function onTargetChange(): void {
  form.negativeAction = "";
  form.addKeywordAction = "";
}

// ── 表单验证 ──
const formRules = {
  name: [{ required: true, message: "请输入规则名称", trigger: "blur" }],
  shops: [
    {
      validator: (_: any, v: any, cb: any) => {
        if (!v?.length) cb(new Error("请选择适用店铺"));
        else cb();
      },
      trigger: "change",
    },
  ],
};

// ── 冲突检测 ──
const ORDERED_OPS: Record<string, number> = { ">": 1, ">=": 2, "<=": 3, "<": 4 };
function getConditionConflict(cSet: { conditions: ConditionWithRange[] }): string | null {
  const conds = cSet.conditions;
  for (let i = 0; i < conds.length; i++) {
    for (let j = i + 1; j < conds.length; j++) {
      const a = conds[i],
        b = conds[j];
      if (a.metric !== b.metric || a.isRange || b.isRange) continue;
      const ao = ORDERED_OPS[a.operator] ?? 0,
        bo = ORDERED_OPS[b.operator] ?? 0;
      if (!ao || !bo) continue;
      const av = a.value ?? 0,
        bv = b.value ?? 0;
      if ((ao <= 2 && bo >= 3 && av >= bv) || (bo <= 2 && ao >= 3 && bv >= av))
        return `指标「${a.metric}」条件冲突："${a.operator}${av}" 与 "${b.operator}${bv}" 不可能同时成立`;
      if (ao >= 3 && bo >= 3) return `指标「${a.metric}」条件可能冗余：两个条件均为小于判断`;
      if (ao <= 2 && bo <= 2) return `指标「${a.metric}」条件可能冗余：两个条件均为大于判断`;
    }
  }
  return null;
}

// ── 选项加载 ──
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
    if (!isEdit.value) form.shops = shopOptions.value.map((o) => o.value);
  } catch {
    /* noop */
  }
}

// ── 全选 ──
function onSelectChange(values: any[], options: any[], field: string): void {
  const idx = values.indexOf(SELECT_ALL_MARKER);
  if (idx === -1) return;
  (form as any)[field] =
    values.length - 1 >= options.length ? [] : options.map((o: any) => o.value);
}

// ── 条件组操作 ──
function addConditionSet(): void {
  form.conditionSets.push({ days: 30, conditions: [{ metric: "acos", operator: ">", value: 30 }] });
}
function removeConditionSet(idx: number): void {
  if (form.conditionSets.length > 1) form.conditionSets.splice(idx, 1);
}
function addCondition(setIdx: number): void {
  form.conditionSets[setIdx].conditions.push({ metric: "clicks", operator: ">", value: 1 });
}
function removeCondition(setIdx: number, condIdx: number): void {
  const c = form.conditionSets[setIdx].conditions;
  if (c.length > 1) c.splice(condIdx, 1);
}
function toggleConditionRange(cSet: { conditions: ConditionWithRange[] }, condIdx: number): void {
  const c = cSet.conditions[condIdx];
  if (c.isRange) {
    c.isRange = false;
    c.value2 = undefined;
    c.operator2 = undefined;
  } else {
    c.isRange = true;
    c.operator2 = ">";
    c.value2 = 0;
  }
}
function isPercentMetric(m: string): boolean {
  return ["acos", "ctr", "cvr", "spendsPercent", "adsSalesPercent"].includes(m);
}

// ── 操作列表 ──
function addBidAction(): void {
  form.bidActions.push({ type: "bid_percent_decrease", value: 0, limit: null });
}
function addBudgetAction(): void {
  form.budgetActions.push({ type: "budget_increase", value: 0, limit: null });
}

// ── 弹窗 ──
function open(data?: Partial<RuleFormData> | null): void {
  Object.assign(form, createEmptyForm());
  shopSearch.value = "";
  isEdit.value = false;
  if (data) {
    isEdit.value = true;
    const raw = JSON.parse(JSON.stringify(data));
    raw.conditionSets?.forEach((cs: any) =>
      cs.conditions?.forEach((c: any) => {
        if (c.isRange == null) c.isRange = !!c.value2;
      })
    );
    Object.assign(form, raw);
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
  for (const cs of form.conditionSets) {
    if (getConditionConflict(cs)) {
      ElMessage.warning("存在冲突的条件，请修正后提交");
      return;
    }
  }
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
  :deep(.el-divider) {
    margin: 20px 0 16px;
  }
  :deep(.el-divider__text) {
    font-size: 13px;
    font-weight: 700;
    color: #374151;
    background: #fff;
  }
  :deep(.el-form-item) {
    margin-bottom: 16px;
  }
  :deep(.el-form-item__label) {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
  }
  :deep(.el-select) {
    --el-select-border-color-hover: #409eff;
    --el-select-input-focus-border-color: #409eff;
  }
  :deep(.el-select .el-input__wrapper) {
    border-radius: 6px;
    transition: box-shadow 0.15s;
    &.is-focus {
      box-shadow: 0 0 0 1px #409eff inset;
    }
  }
  :deep(.el-input__wrapper) {
    border-radius: 6px;
  }
}

.mb-2 {
  margin-bottom: 10px;
}
.mb-4 {
  margin-bottom: 16px;
}
:deep(.el-radio-button__inner) {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 6px !important;
}
.rule-relation-alert {
  margin: 8px 0 4px;
  :deep(.el-alert__title) {
    font-size: 13px;
  }
  p {
    margin: 2px 0;
    font-size: 12px;
    line-height: 1.5;
  }
}

.effective-days-row {
  display: flex;
  gap: 10px;
  align-items: center;
}
.effective-prefix {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
.effective-suffix {
  font-size: 13px;
  color: #909399;
}
.effective-date-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.date-sep {
  font-size: 13px;
  color: #909399;
}
.effective-date-hint {
  margin-left: 4px;
  font-size: 12px;
  color: #909399;
}

.field-setting-item :deep(.el-form-item__content) {
  flex-wrap: nowrap;
}
.field-setting-row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
  .el-checkbox {
    flex-shrink: 0;
    margin-right: 0;
  }
}

.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

// ── 比对对象 ──
.comparison-target-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
.comparison-checkboxes {
  display: flex;
  gap: 8px;
}
.comparison-sep {
  font-size: 20px;
  color: #dcdfe6;
}
.comparison-radios {
  display: flex;
  gap: 8px;
}

// ── 条件组 ──
.condition-sets {
  margin-top: 10px;
}
.condition-set-card {
  padding: 16px 18px;
  margin-bottom: 10px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  transition: border-color 0.15s;
  &:hover {
    border-color: #c6ddfc;
  }
}
.condition-set-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.condition-set-label {
  flex: 1;
  font-size: 13px;
  font-weight: 700;
  color: #303133;
}
.condition-set-days {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #f0f2f5;
  border-radius: 6px;
}
.days-prefix {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
.days-suffix {
  font-size: 12px;
  color: #909399;
}
.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.condition-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.range-placeholder {
  min-width: 20px;
  font-size: 12px;
  color: #909399;
}
.range-var {
  display: inline-block;
  padding: 1px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 4px;
}
.conflict-alert {
  margin-top: 4px;
  :deep(.el-alert__title) {
    font-size: 12px;
  }
}
.cond-remove-btn,
.cond-toggle-btn {
  flex-shrink: 0;
}
.cond-toggle-btn {
  font-size: 11px;
}
.add-set-btn {
  margin-top: 4px;
}

.input-suffix {
  font-size: 12px;
  color: #909399;
}

// ── 执行操作 ──
.action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.action-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.action-unit {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}
.action-limit-label {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}
.add-action-btn {
  margin-top: 4px;
}

// ── 搜索词专属 ──
.keyword-add-panel {
  padding: 12px 16px;
  margin-top: 10px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.kadd-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
  &:last-child {
    margin-bottom: 0;
  }
}
.kadd-label {
  flex-shrink: 0;
  width: 70px;
  font-size: 13px;
  color: #606266;
}
.keyword-add-note {
  margin-top: 10px;
  :deep(.el-alert__title) {
    font-size: 12px;
  }
  p {
    margin: 2px 0;
    font-size: 12px;
    line-height: 1.5;
  }
}
</style>
