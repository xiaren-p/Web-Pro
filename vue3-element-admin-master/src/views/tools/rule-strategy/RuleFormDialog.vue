<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="1100px"
    destroy-on-close
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="formRules"
      label-width="110px"
      class="rule-form"
      :disabled="isReadonly"
    >
      <!-- ========== 基础信息 ========== -->
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
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          tag-effect="dark"
          style="width: 100%"
          placeholder="请选择适用店铺"
          popper-class="rule-select-popper"
          :filter-method="(v: string) => (shopSearch = v)"
          @change="(vals: any[]) => onSelectChange(vals, filteredShopOptions, 'shops')"
        >
          <el-option :key="ALL_MARKER" label="全选 / 取消全选" :value="ALL_MARKER" />
          <el-option
            v-for="opt in filteredShopOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <!-- ========== 广告类型 ========== -->
      <el-divider content-position="left">广告类型</el-divider>
      <el-form-item label="广告类型">
        <el-select v-model="form.adType" style="width: 220px" @change="onAdTypeChange">
          <el-option value="all" label="不限" />
          <el-option value="manual" label="手动广告 (MANUAL)" />
          <el-option value="auto" label="自动广告 (AUTO)" />
        </el-select>
      </el-form-item>

      <!-- ========== 生效时间 ========== -->
      <el-divider content-position="left">生效时间</el-divider>
      <el-form-item label="生效周期">
        <div class="effective-row">
          <el-select v-model="form.effectiveType" style="width: 180px" placeholder="选择生效周期">
            <el-option value="within_days" label="指定天数内" />
            <el-option value="beyond_days" label="指定天数外" />
            <el-option value="date_range" label="日期范围" />
          </el-select>
          <template v-if="form.effectiveType !== 'date_range'">
            <span class="fx-label">最近</span>
            <el-select
              :model-value="form.effectiveDaysStart ? form.effectiveDaysStart + '天' : ''"
              style="width: 110px"
              placeholder="起始天"
              filterable
              allow-create
              default-first-option
              @update:model-value="(v: any) => handleDaysChange(v, 'start')"
            >
              <el-option v-for="d in DAY_PRESETS" :key="d" :label="d + '天'" :value="d" />
            </el-select>
            <span class="fx-sep">至</span>
            <el-select
              :model-value="form.effectiveDaysEnd ? form.effectiveDaysEnd + '天' : ''"
              style="width: 110px"
              placeholder="结束天"
              filterable
              allow-create
              default-first-option
              @update:model-value="(v: any) => handleDaysChange(v, 'end')"
            >
              <el-option v-for="d in DAY_PRESETS" :key="d" :label="d + '天'" :value="d" />
            </el-select>
            <span class="fx-hint">
              {{ form.effectiveType === "beyond_days" ? "之外的广告实体" : "内的广告实体" }}
            </span>
          </template>
          <template v-else>
            <div class="effective-date-row">
              <el-select
                v-model="form.effectiveStart"
                placeholder="月"
                style="width: 72px"
                clearable
              >
                <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
              </el-select>
              <el-select
                v-model="form.effectiveStartDay"
                placeholder="日"
                style="width: 72px"
                :disabled="!form.effectiveStart"
                clearable
              >
                <el-option v-for="d in 31" :key="d" :label="d + '日'" :value="String(d)" />
              </el-select>
              <span class="date-sep">至</span>
              <el-select v-model="form.effectiveEnd" placeholder="月" style="width: 72px" clearable>
                <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="String(m)" />
              </el-select>
              <el-select
                v-model="form.effectiveEndDay"
                placeholder="日"
                style="width: 72px"
                :disabled="!form.effectiveEnd"
                clearable
              >
                <el-option v-for="d in 31" :key="d" :label="d + '日'" :value="String(d)" />
              </el-select>
              <span class="effective-date-hint">每年此时段生效</span>
            </div>
          </template>
        </div>
      </el-form-item>

      <!-- ========== 比对对象 ========== -->
      <el-divider content-position="left">比对对象</el-divider>
      <el-form-item label="比对对象">
        <el-radio-group
          v-model="form.comparisonTarget"
          class="comparison-radios"
          @change="onTargetChange"
        >
          <el-radio value="campaign">广告活动</el-radio>
          <el-radio value="ad_group" :disabled="true">广告组（开发中）</el-radio>
          <el-radio value="search_terms">用户搜索词</el-radio>
          <el-radio value="targeting">投放</el-radio>
          <el-radio value="negative_targeting">否定投放</el-radio>
        </el-radio-group>

        <!-- 投放子选项 -->
        <div v-if="form.comparisonTarget === 'targeting'" class="targeting-sub-row">
          <el-checkbox-group v-model="form.comparisonMultiTargets" class="comparison-checkboxes">
            <el-checkbox value="targeting" :disabled="form.adType === 'manual'">
              定位组投放
            </el-checkbox>
            <el-checkbox value="keyword" :disabled="form.adType === 'auto'">关键词投放</el-checkbox>
            <el-checkbox value="product_targeting" :disabled="form.adType === 'auto'">
              商品投放
            </el-checkbox>
          </el-checkbox-group>
          <span
            v-if="form.comparisonMultiTargets.length === 0"
            class="form-hint"
            style="color: #e6a23c"
          >
            请至少选择一种投放类型
          </span>
        </div>
      </el-form-item>

      <!-- ========== 字段设置 ========== -->
      <el-divider content-position="left">字段设置</el-divider>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="归类">
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedCategories">不限</el-checkbox>
              <el-select
                v-model="form.categories"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                tag-effect="dark"
                style="flex: 1"
                placeholder="选择归类"
                :disabled="form.unlimitedCategories"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, assortOptions, 'categories')"
              >
                <el-option :key="ALL_MARKER" label="全选 / 取消全选" :value="ALL_MARKER" />
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
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedManagers">不限</el-checkbox>
              <el-select
                v-model="form.managers"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                tag-effect="dark"
                style="flex: 1"
                placeholder="选择负责人"
                :disabled="form.unlimitedManagers"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, managerOptions, 'managers')"
              >
                <el-option :key="ALL_MARKER" label="全选 / 取消全选" :value="ALL_MARKER" />
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
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedTags">不限</el-checkbox>
              <el-select
                v-model="form.tags"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                tag-effect="dark"
                style="flex: 1"
                placeholder="选择标签"
                :disabled="form.unlimitedTags"
                popper-class="rule-select-popper"
                @change="(vals: any[]) => onSelectChange(vals, labelOptions, 'tags')"
              >
                <el-option :key="ALL_MARKER" label="全选 / 取消全选" :value="ALL_MARKER" />
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

      <!-- 自动定位组（AUTO + 投放 + 勾选了定位组投放 时显示） -->
      <el-row v-if="showAutoTargetingField" :gutter="16">
        <el-col :span="8">
          <el-form-item label="自动定位组">
            <div class="field-setting-row">
              <el-checkbox v-model="form.unlimitedAutoTargeting">不限</el-checkbox>
              <el-select
                v-model="form.autoTargetingGroups"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                :max-collapse-tags="1"
                tag-effect="dark"
                style="flex: 1"
                placeholder="选择类型"
                :disabled="form.unlimitedAutoTargeting"
              >
                <el-option value="close_match" label="同类商品" />
                <el-option value="loose_match" label="紧密匹配" />
                <el-option value="substitutes" label="关联商品" />
                <el-option value="complements" label="宽泛匹配" />
              </el-select>
            </div>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- ========== 规则关系 ========== -->
      <el-alert
        title="规则关系说明"
        type="info"
        :closable="false"
        show-icon
        class="rule-relation-alert"
      >
        <template #default>
          <p>
            所有条件组必须
            <b>全部满足</b>
            才会执行（
            <b>并</b>
            关系），组内条件同样为
            <b>并</b>
            关系（全部满足才触发）。
          </p>
        </template>
      </el-alert>

      <!-- ========== 规则设置 ========== -->
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
          placeholder="选择关联的分时规则（非必选）"
          popper-class="rule-select-popper"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
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
          placeholder="选择排除的分时规则（非必选）"
          popper-class="rule-select-popper"
        >
          <el-option
            v-for="opt in timeRuleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <!-- 条件组 -->
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
              删除
            </el-button>
          </div>
          <!-- 条件对象（投放/搜索词场景） -->
          <div v-if="showCondTarget" class="condition-set-days">
            <span class="target-label">条件对象</span>
            <el-select
              :model-value="cSet.target || 'campaign'"
              style="width: 140px"
              size="small"
              @update:model-value="
                (v: any) => {
                  cSet.target = v;
                }
              "
            >
              <el-option
                v-for="o in getCondTargetOpts()"
                :key="o.value"
                :label="o.label"
                :value="o.value"
                :disabled="o.disabled"
              />
            </el-select>
          </div>
          <div class="condition-set-days">
            <el-select
              :model-value="cSet.days === 0 ? '生命周期' : cSet.days ? cSet.days + '天' : ''"
              style="width: 130px"
              size="small"
              placeholder="天数"
              filterable
              allow-create
              default-first-option
              @update:model-value="(v: any) => handleCondDaysChange(cSet, v)"
            >
              <el-option label="生命周期" :value="0" />
              <el-option v-for="d in COND_DAY_PRESETS" :key="d" :label="d + '天'" :value="d" />
            </el-select>
            <span v-if="cSet.days !== 0" class="days-suffix">内全部满足才触发</span>
            <span v-else class="days-suffix">使用规则生效天数为条件窗口</span>
          </div>
          <div class="conditions-list">
            <div v-for="(cond, condIdx) in cSet.conditions" :key="condIdx" class="condition-row">
              <el-select
                v-model="cond.metric"
                style="width: 140px"
                size="small"
                placeholder="指标"
                @change="
                  cond.operator = '>';
                  cond.value2 = undefined;
                "
              >
                <el-option
                  v-for="m in availableMetricOptions"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                />
              </el-select>
              <!-- ===== 范围模式：值 X < metric < Y ===== -->
              <template v-if="cond.isRange">
                <el-input-number
                  v-model="cond.value"
                  size="small"
                  style="width: 100px"
                  :min="0"
                  :precision="2"
                  :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                  controls-position="right"
                />
                <el-select v-model="cond.operator2" style="width: 64px" size="small">
                  <el-option
                    v-for="o in operatorOptions"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
                <span class="range-var">{{ cond.metric }}</span>
                <el-select v-model="cond.operator" style="width: 64px" size="small">
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
                  style="width: 100px"
                  :min="0"
                  :precision="2"
                  :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                  controls-position="right"
                />
              </template>
              <!-- ===== 单值模式：metric > X ===== -->
              <template v-else>
                <el-select v-model="cond.operator" style="width: 64px" size="small">
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
                  style="width: 120px"
                  :min="0"
                  :precision="2"
                  :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                  controls-position="right"
                />
              </template>
              <el-button
                text
                type="primary"
                size="small"
                style="flex-shrink: 0; font-size: 11px"
                @click="toggleConditionRange(cSet, condIdx)"
              >
                {{ cond.isRange ? "切为单值" : "切为范围" }}
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

      <!-- ========== 执行操作 ========== -->
      <el-divider content-position="left">执行操作</el-divider>

      <!-- D. 广告组（开发中） -->
      <template v-if="form.comparisonTarget === 'ad_group'">
        <el-alert title="广告组规则开发中，敬请期待" type="info" :closable="false" show-icon />
      </template>

      <!-- A. 搜索词 -->
      <template v-else-if="form.comparisonTarget === 'search_terms'">
        <el-form-item label="否定操作">
          <div class="action-single-row">
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
            <span class="form-hint">可选，对匹配的用户搜索词添加否定关键词</span>
          </div>
        </el-form-item>
        <el-form-item label="关键词投放">
          <div class="action-single-row">
            <el-select
              v-model="form.addKeywordAction"
              style="width: 320px"
              placeholder="添加关键词到手动广告活动（可选）"
              clearable
            >
              <el-option
                v-for="opt in addKeywordActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <span class="form-hint">可选，可与否定操作同时调整</span>
          </div>
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
        </el-form-item>
      </template>

      <!-- C. 广告活动 -->
      <template v-else-if="form.comparisonTarget === 'campaign'">
        <el-alert
          title="投放竞价与预算操作各自独立，可同时调整也可仅选其一"
          type="info"
          :closable="false"
          show-icon
          class="mb-4"
        />

        <!-- C. 投放竞价操作 -->
        <div class="tba-section">
          <div class="tba-header">
            <span class="tba-title">投放竞价操作</span>
            <el-button text type="primary" size="small" @click="addTargetingBidAction">
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
          </div>
          <div v-for="(tba, idx) in form.targetingBidActions" :key="idx" class="tba-card">
            <div class="tba-card-header">
              <span class="tba-card-label">投放竞价 {{ idx + 1 }}</span>
              <div class="tba-card-header-actions">
                <el-button text size="small" @click="clearTbaConditions(tba)">
                  <el-icon><Delete /></el-icon>
                  清空条件
                </el-button>
                <el-button text type="danger" size="small" @click="removeTargetingBidAction(idx)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
            <!-- 定位组（AUTO） / 投放对象（MANUAL） -->
            <el-form-item
              :label="form.adType === 'manual' ? '投放对象' : '定位组'"
              label-width="80px"
            >
              <div class="field-setting-row">
                <el-checkbox v-model="tba.unlimitedTargeting">不限</el-checkbox>
                <el-select
                  v-model="tba.targetingGroups"
                  multiple
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  :max-collapse-tags="1"
                  tag-effect="dark"
                  style="flex: 1"
                  :placeholder="form.adType === 'manual' ? '选择投放对象' : '选择定位组类型'"
                  :disabled="tba.unlimitedTargeting"
                >
                  <template v-if="form.adType === 'manual'">
                    <el-option value="keyword" label="关键词" />
                    <el-option value="product_targeting" label="商品" />
                  </template>
                  <template v-else>
                    <el-option value="close_match" label="同类商品" />
                    <el-option value="loose_match" label="紧密匹配" />
                    <el-option value="substitutes" label="关联商品" />
                    <el-option value="complements" label="宽泛匹配" />
                  </template>
                </el-select>
              </div>
            </el-form-item>

            <!-- 条件 -->
            <el-form-item label="条件" label-width="80px">
              <el-button text type="primary" size="small" @click="addTbaCondition(tba)">
                <el-icon><Plus /></el-icon>
                添加条件
              </el-button>
              <template v-if="hasTbaConditions(tba)">
                <el-button
                  text
                  type="primary"
                  size="small"
                  style="margin-left: 8px"
                  @click="toggleTbaConds(tba)"
                >
                  <el-icon><View /></el-icon>
                  {{ (tba as any)._showConds ? "收起条件" : "查看条件" }}
                </el-button>
              </template>
            </el-form-item>
            <template v-if="(tba as any)._showConds">
              <div class="tba-conditions">
                <div
                  v-for="(cSet, csIdx) in tba.conditionSets"
                  :key="csIdx"
                  class="tba-condition-set"
                >
                  <div class="tba-cs-header">
                    <span>条件组 {{ csIdx + 1 }}</span>
                    <el-select
                      :model-value="
                        cSet.days === 0 ? '生命周期' : cSet.days ? cSet.days + '天' : ''
                      "
                      style="width: 110px"
                      size="small"
                      placeholder="天数"
                      filterable
                      allow-create
                      default-first-option
                      @update:model-value="(v: any) => handleCondDaysChange(cSet, v)"
                    >
                      <el-option label="生命周期" :value="0" />
                      <el-option
                        v-for="d in COND_DAY_PRESETS"
                        :key="d"
                        :label="d + '天'"
                        :value="d"
                      />
                    </el-select>
                    <span style="font-size: 12px; color: #909399">
                      {{ cSet.days !== 0 ? "内全部满足" : "使用生效天数" }}
                    </span>
                  </div>
                  <div
                    v-for="(cond, condIdx) in cSet.conditions"
                    :key="condIdx"
                    class="condition-row"
                  >
                    <el-select
                      v-model="cond.metric"
                      style="width: 130px"
                      size="small"
                      placeholder="指标"
                      @change="
                        cond.operator = '>';
                        cond.value2 = undefined;
                      "
                    >
                      <el-option
                        v-for="m in availableMetricOptions"
                        :key="m.value"
                        :label="m.label"
                        :value="m.value"
                      />
                    </el-select>
                    <!-- 范围模式：值 X < metric < Y -->
                    <template v-if="cond.isRange">
                      <el-input-number
                        v-model="cond.value"
                        size="small"
                        style="width: 100px"
                        :min="0"
                        :precision="2"
                        :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                        controls-position="right"
                      />
                      <el-select v-model="cond.operator2" style="width: 64px" size="small">
                        <el-option
                          v-for="o in operatorOptions"
                          :key="o.value"
                          :label="o.label"
                          :value="o.value"
                        />
                      </el-select>
                      <span class="range-var">{{ cond.metric }}</span>
                      <el-select v-model="cond.operator" style="width: 64px" size="small">
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
                        style="width: 100px"
                        :min="0"
                        :precision="2"
                        :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                        controls-position="right"
                      />
                    </template>
                    <!-- 单值模式：metric > X -->
                    <template v-else>
                      <el-select v-model="cond.operator" style="width: 64px" size="small">
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
                        style="width: 120px"
                        :min="0"
                        :precision="2"
                        :step="isPercentMetric(cond.metric) ? 1 : 0.01"
                        controls-position="right"
                      />
                    </template>
                    <el-button
                      text
                      type="primary"
                      size="small"
                      style="flex-shrink: 0; font-size: 11px"
                      @click="toggleCondRange(cSet, condIdx)"
                    >
                      {{ cond.isRange ? "切为单值" : "切为范围" }}
                    </el-button>
                    <el-button
                      v-if="cSet.conditions.length > 1"
                      text
                      type="danger"
                      size="small"
                      @click="cSet.conditions.splice(condIdx, 1)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button
                    text
                    type="primary"
                    size="small"
                    @click="cSet.conditions.push({ metric: 'clicks', operator: '>', value: 1 })"
                  >
                    <el-icon><Plus /></el-icon>
                    添加条件
                  </el-button>
                </div>
                <el-button
                  text
                  type="primary"
                  size="small"
                  style="margin-top: 4px"
                  @click="
                    tba.conditionSets.push({
                      target: 'campaign',
                      days: 7,
                      conditions: [{ metric: 'acos', operator: '>', value: 30 }],
                    })
                  "
                >
                  <el-icon><Plus /></el-icon>
                  新增条件组
                </el-button>
              </div>
            </template>

            <!-- 竞价操作 -->
            <el-form-item label="竞价操作" label-width="80px">
              <div class="action-single-row">
                <el-select
                  v-model="tba.bidAction.type"
                  style="width: 200px"
                  placeholder="选择竞价操作（可选）"
                  clearable
                  @change="
                    !tba.bidAction.type && ((tba.bidAction.value = 0), (tba.bidAction.limit = null))
                  "
                >
                  <el-option
                    v-for="opt in bidActionOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
                <template v-if="tba.bidAction.type && isBidValueAction(tba.bidAction.type)">
                  <el-input-number
                    v-model="tba.bidAction.value"
                    style="width: 120px"
                    :min="0"
                    :precision="2"
                    :max="tba.bidAction.type.includes('percent') ? 200 : 999999"
                    :step="tba.bidAction.type.includes('percent') ? 1 : 0.1"
                    controls-position="right"
                  />
                  <span class="action-unit">
                    {{ tba.bidAction.type.includes("percent") ? "%" : "€" }}
                  </span>
                </template>
                <template v-if="tba.bidAction.type && isIncreaseType(tba.bidAction.type)">
                  <span class="action-limit-label">最高不超过</span>
                  <el-input-number
                    v-model="tba.bidAction.limit"
                    style="width: 120px"
                    :min="0"
                    :precision="2"
                    :step="0.1"
                    controls-position="right"
                  />
                  <span class="action-unit">€</span>
                </template>
                <template v-if="tba.bidAction.type === 'bid_fixed_decrease'">
                  <span class="action-limit-label">最低不低于</span>
                  <el-input-number
                    v-model="tba.bidAction.limit"
                    style="width: 120px"
                    :min="0"
                    :precision="2"
                    :step="0.1"
                    controls-position="right"
                  />
                  <span class="action-unit">€</span>
                </template>
              </div>
            </el-form-item>
          </div>
        </div>

        <!-- 广告组默认竞价（开发中） -->
        <el-form-item label="广告组竞价">
          <el-select style="width: 280px" placeholder="广告组默认竞价（开发中）" disabled>
            <el-option label="开发中，敬请期待" value="" />
          </el-select>
        </el-form-item>

        <!-- 预算操作 -->
        <el-form-item label="预算操作">
          <div class="action-single-row">
            <el-select
              v-model="form.budgetAction.type"
              style="width: 220px"
              placeholder="选择预算操作（可选）"
              clearable
              @change="onBudgetActionClear"
            >
              <el-option
                v-for="opt in budgetActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.budgetAction.type && form.budgetAction.type !== 'no_adjust'">
              <el-input-number
                v-model="form.budgetAction.value"
                style="width: 120px"
                :min="1"
                :step="1"
                :precision="0"
                controls-position="right"
              />
              <span class="action-unit">€/天</span>
              <span class="action-limit-label">不超过</span>
              <el-input-number
                v-model="form.budgetAction.limit"
                style="width: 120px"
                :min="0"
                :precision="2"
                :step="0.1"
                controls-position="right"
              />
              <span class="action-unit">€/天</span>
            </template>
          </div>
        </el-form-item>

        <!-- 其他操作 -->
        <el-form-item label="其他操作">
          <div class="action-single-row">
            <el-select
              v-model="form.otherAction.type"
              style="width: 200px"
              placeholder="选择其他操作（可选）"
              clearable
            >
              <el-option
                v-for="opt in otherActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.otherAction.type && form.otherAction.type !== 'no_other'">
              <span class="action-limit-label">是否通知</span>
              <el-switch
                v-model="form.otherAction.notify"
                active-text="通知"
                inactive-text="不通知"
                inline-prompt
              />
            </template>
          </div>
        </el-form-item>
      </template>

      <!-- B. 投放 -->
      <template v-else-if="form.comparisonTarget === 'targeting'">
        <el-alert
          title="竞价操作、预算操作、其他操作各自独立，可同时调整也可仅选其一"
          type="info"
          :closable="false"
          show-icon
          class="mb-4"
        />

        <el-form-item label="竞价操作">
          <div class="action-single-row">
            <el-select
              v-model="form.bidAction.type"
              style="width: 200px"
              placeholder="选择竞价操作（可选）"
              clearable
              @change="onBidActionClear"
            >
              <el-option
                v-for="opt in bidActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.bidAction.type && isBidValueAction(form.bidAction.type)">
              <el-input-number
                v-model="form.bidAction.value"
                style="width: 140px"
                :min="0"
                :precision="2"
                :max="form.bidAction.type.includes('percent') ? 200 : 999999"
                :step="form.bidAction.type.includes('percent') ? 1 : 0.1"
                controls-position="right"
              />
              <span class="action-unit">
                {{ form.bidAction.type.includes("percent") ? "%" : "€" }}
              </span>
            </template>
            <template v-if="form.bidAction.type && isIncreaseType(form.bidAction.type)">
              <span class="action-limit-label">最高不超过</span>
              <el-input-number
                v-model="form.bidAction.limit"
                style="width: 130px"
                :min="0"
                :precision="2"
                :step="0.1"
                controls-position="right"
              />
              <span class="action-unit">€</span>
            </template>
            <template v-if="form.bidAction.type === 'bid_fixed_decrease'">
              <span class="action-limit-label">最低不低于</span>
              <el-input-number
                v-model="form.bidAction.limit"
                style="width: 130px"
                :min="0"
                :precision="2"
                :step="0.1"
                controls-position="right"
              />
              <span class="action-unit">€</span>
            </template>
          </div>
        </el-form-item>

        <el-form-item label="预算操作">
          <div class="action-single-row">
            <el-select
              v-model="form.budgetAction.type"
              style="width: 220px"
              placeholder="选择预算操作（可选）"
              clearable
              @change="onBudgetActionClear"
            >
              <el-option
                v-for="opt in budgetActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.budgetAction.type && form.budgetAction.type !== 'no_adjust'">
              <el-input-number
                v-model="form.budgetAction.value"
                style="width: 120px"
                :min="1"
                :step="1"
                :precision="0"
                controls-position="right"
              />
              <span class="action-unit">€/天</span>
              <span class="action-limit-label">不超过</span>
              <el-input-number
                v-model="form.budgetAction.limit"
                style="width: 120px"
                :min="0"
                :precision="2"
                :step="0.1"
                controls-position="right"
              />
              <span class="action-unit">€/天</span>
            </template>
          </div>
        </el-form-item>

        <el-form-item label="其他操作">
          <div class="action-single-row">
            <el-select
              v-model="form.otherAction.type"
              style="width: 200px"
              placeholder="选择其他操作（可选）"
              clearable
            >
              <el-option
                v-for="opt in otherActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.otherAction.type && form.otherAction.type !== 'no_other'">
              <span class="action-limit-label">是否通知</span>
              <el-switch
                v-model="form.otherAction.notify"
                active-text="通知"
                inactive-text="不通知"
                inline-prompt
              />
            </template>
          </div>
        </el-form-item>
      </template>

      <!-- D. 否定投放：仅显示其他操作 -->
      <template v-else-if="form.comparisonTarget === 'negative_targeting'">
        <el-alert
          title="否定投放仅支持其他操作（暂停/归档）"
          type="warning"
          :closable="false"
          show-icon
          class="mb-4"
        />

        <el-form-item label="其他操作">
          <div class="action-single-row">
            <el-select
              v-model="form.otherAction.type"
              style="width: 200px"
              placeholder="选择其他操作（可选）"
              clearable
            >
              <el-option
                v-for="opt in otherActionOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <template v-if="form.otherAction.type && form.otherAction.type !== 'no_other'">
              <span class="action-limit-label">是否通知</span>
              <el-switch
                v-model="form.otherAction.notify"
                active-text="通知"
                inactive-text="不通知"
                inline-prompt
              />
            </template>
          </div>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">{{ footerCloseText }}</el-button>
      <el-button v-if="!isReadonly" type="primary" :loading="saving" @click="handleSubmit">
        {{ isEdit ? "保存" : "创建" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * SP 广告规则策略 — 规则创建/编辑弹窗。
 * 支持广告类型联动、比对对象差异化操作。
 *
 * 所属板块：tools / 广告规则策略。
 */
import type {
  RuleFormData,
  ConditionWithRange,
  TargetingBidAction,
} from "@/views/tools/rule-strategy/types";
import { ref, reactive, computed } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Delete, View } from "@element-plus/icons-vue";
import {
  getShopOptions,
  getManagerOptions,
  getAssortOptions,
  getLabelOptions,
  getTimePricingList,
} from "@/api/ads";

defineOptions({ name: "RuleFormDialog" });
const emit = defineEmits<{ (e: "saved", data: RuleFormData): void }>();

const ALL_MARKER = "__select_all__";
const shopSearch = ref("");
const DAY_PRESETS = [0, 7, 15, 30, 60, 90, 180, 365];
const COND_DAY_PRESETS = [7, 15, 30, 60, 90, 180, 365];

function blankAction() {
  return { type: "", value: 0, limit: null } as const;
}

function blankTba(): TargetingBidAction & { _showConds?: boolean } {
  return {
    targetingGroups: [],
    unlimitedTargeting: false,
    conditionSets: [{ target: "campaign", days: 7, conditions: [] }],
    bidAction: { type: "", value: 0, limit: null },
    _showConds: false,
  };
}

function createEmptyForm(): RuleFormData {
  return {
    id: "",
    name: "",
    shops: [],
    status: "active",
    adType: "all",
    effectiveType: "within_days",
    effectiveDaysStart: 8,
    effectiveDaysEnd: 30,
    effectiveStart: "",
    effectiveStartDay: "",
    effectiveEnd: "",
    effectiveEndDay: "",
    comparisonTarget: "campaign",
    comparisonMultiTargets: [],
    categories: [],
    unlimitedCategories: true,
    managers: [],
    unlimitedManagers: true,
    tags: [],
    unlimitedTags: true,
    autoTargetingGroups: [],
    unlimitedAutoTargeting: true,
    conditionSets: [
      { target: "campaign", days: 30, conditions: [{ metric: "acos", operator: ">", value: 30 }] },
    ],
    linkedTimeRules: [],
    linkedTimeRulesExclude: [],
    targetingBidActions: [],
    bidAction: blankAction(),
    budgetAction: blankAction(),
    otherAction: { type: "", notify: true },
    negativeAction: "",
    addKeywordAction: "",
    addKeywordMatchType: "broad",
    addKeywordBidType: "actual_cpc",
    addKeywordMaxBid: 0.2,
    addKeywordFixedBid: null,
  };
}

const visible = ref(false);
const formRef = ref<any>(null);
const isEdit = ref(false);
const isReadonly = ref(false);
const saving = ref(false);

/** 对话框标题 */
const dialogTitle = computed(() =>
  isReadonly.value ? "查看规则" : isEdit.value ? "编辑规则" : "创建规则"
);

/** 底部关闭按钮文本 */
const footerCloseText = computed(() => (isReadonly.value ? "关闭" : "取消"));
const form = reactive<RuleFormData>(createEmptyForm());

const shopOptions = ref<any[]>([]);
const managerOptions = ref<any[]>([]);
const assortOptions = ref<{ value: string; label: string }[]>([]);
const labelOptions = ref<{ value: string; label: string }[]>([]);
const timeRuleOptions = ref<any[]>([]);

const filteredShopOptions = computed(() =>
  !shopSearch.value
    ? shopOptions.value
    : shopOptions.value.filter((o: any) =>
        o.label.toLowerCase().includes(shopSearch.value.toLowerCase())
      )
);

const showAutoTargetingField = computed(
  () =>
    form.adType === "auto" &&
    form.comparisonTarget === "targeting" &&
    form.comparisonMultiTargets.includes("targeting")
);

/** 是否在每个条件前显示条件对象下拉（仅投放/搜索词） */
const showCondTarget = computed(() =>
  ["targeting", "search_terms"].includes(form.comparisonTarget)
);

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

/** 否定投放场景下的受限指标：花费、ACoS、广告销售额 */
const negativeTargetingMetricOptions = [
  { value: "spend", label: "花费" },
  { value: "acos", label: "ACoS (%)" },
  { value: "adsSales", label: "广告销售额" },
];

/** 当前条件组可用的指标（否定投放时受限） */
const availableMetricOptions = computed(() =>
  form.comparisonTarget === "negative_targeting" ? negativeTargetingMetricOptions : metricOptions
);
const operatorOptions = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: ">=", label: "≥" },
  { value: "<=", label: "≤" },
];
const bidActionOptions = [
  { value: "bid_percent_increase", label: "竞价按百分比提高" },
  { value: "bid_fixed_increase", label: "竞价按固定值增加" },
  { value: "bid_percent_decrease", label: "竞价按百分比降低" },
  { value: "bid_fixed_decrease", label: "竞价按固定值减少" },
  { value: "no_adjust", label: "不调整" },
];
const budgetActionOptions = [
  { value: "budget_increase", label: "广告活动预算增加" },
  { value: "budget_decrease", label: "广告活动预算减少" },
  { value: "no_adjust", label: "不调整" },
];
const otherActionOptions = [
  { value: "pause", label: "暂停" },
  { value: "archive", label: "归档" },
  { value: "no_other", label: "不操作" },
];
const negativeActionOptions = [
  { value: "negative_exact", label: "添加精准否定关键词" },
  { value: "negative_phrase", label: "添加否定词组" },
];
const addKeywordActionOptions = [{ value: "add_keyword", label: "添加对应手动广告活动关键词" }];

function isBidValueAction(t: string) {
  return t.startsWith("bid_percent_") || t.startsWith("bid_fixed_");
}
function isIncreaseType(t: string) {
  return t.includes("increase");
}

function onAdTypeChange(): void {
  form.comparisonMultiTargets = form.comparisonMultiTargets.filter((v) => {
    if (form.adType === "auto" && v !== "targeting") return false;
    if (form.adType === "manual" && v === "targeting") return false;
    return true;
  });
}
function onTargetChange(): void {
  form.negativeAction = "";
  form.addKeywordAction = "";
  form.comparisonMultiTargets = [];
  form.otherAction = { type: "", notify: true };
  form.targetingBidActions = [];
}

function getCondTargetOpts() {
  if (form.comparisonTarget === "search_terms") {
    return [
      { value: "campaign", label: "广告活动实体" },
      { value: "ad_group", label: "广告组实体", disabled: true },
      { value: "search_term", label: "搜索词实体" },
    ];
  }
  return [
    { value: "campaign", label: "广告活动实体" },
    { value: "ad_group", label: "广告组实体", disabled: true },
    { value: "targeting", label: "投放实体" },
  ];
}
function onBidActionClear() {
  if (!form.bidAction.type) {
    form.bidAction.value = 0;
    form.bidAction.limit = null;
  }
}
function onBudgetActionClear() {
  if (!form.budgetAction.type) {
    form.budgetAction.value = 0;
    form.budgetAction.limit = null;
  }
}

const formRules = {
  name: [{ required: true, message: "请输入规则名称", trigger: "blur" }],
  shops: [
    {
      validator: (_: any, v: any, cb: any) => (v?.length ? cb() : cb(new Error("请选择适用店铺"))),
      trigger: "change",
    },
  ],
  comparisonTarget: [{ required: true, message: "请选择比对对象", trigger: "change" }],
};

const ORDERED_OPS: Record<string, number> = { ">": 1, ">=": 2, "<=": 3, "<": 4 };
function getConditionConflict(cSet: { conditions: ConditionWithRange[] }): string | null {
  const c = cSet.conditions;
  for (let i = 0; i < c.length; i++) {
    for (let j = i + 1; j < c.length; j++) {
      const a = c[i],
        b = c[j];
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
    if (!isEdit.value) form.shops = shopOptions.value.map((o: any) => o.value);
  } catch {
    /* ignore */
  }
}

function onSelectChange(values: any[], options: any[], field: string): void {
  const i = values.indexOf(ALL_MARKER);
  if (i === -1) return;
  (form as any)[field] =
    values.length - 1 >= options.length ? [] : options.map((o: any) => o.value);
}

function addConditionSet() {
  form.conditionSets.push({
    target: "campaign",
    days: 30,
    conditions: [{ metric: "acos", operator: ">", value: 30 }],
  });
}
function removeConditionSet(i: number) {
  if (form.conditionSets.length > 1) form.conditionSets.splice(i, 1);
}
function addCondition(setIdx: number) {
  form.conditionSets[setIdx].conditions.push({ metric: "clicks", operator: ">", value: 1 });
}
function removeCondition(setIdx: number, condIdx: number) {
  const c = form.conditionSets[setIdx].conditions;
  if (c.length > 1) c.splice(condIdx, 1);
}
function toggleCondRange(cSet: { conditions: ConditionWithRange[] }, condIdx: number) {
  toggleConditionRange(cSet, condIdx);
}

function toggleConditionRange(cSet: { conditions: ConditionWithRange[] }, condIdx: number) {
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

function addTargetingBidAction() {
  form.targetingBidActions.push(blankTba() as any);
}
function toggleTbaConds(tba: any) {
  tba._showConds = !tba._showConds;
}
function removeTargetingBidAction(i: number) {
  form.targetingBidActions.splice(i, 1);
}
function clearTbaConditions(tba: any) {
  tba.conditionSets = [{ target: "campaign", days: 7, conditions: [] }];
  tba._showConds = false;
}

function hasTbaConditions(tba: any): boolean {
  return tba.conditionSets.some((cs: any) => cs.conditions?.length > 0);
}

function addTbaCondition(tba: any) {
  if (!tba.conditionSets?.length)
    tba.conditionSets = [{ target: "campaign", days: 7, conditions: [] }];
  tba.conditionSets[0].conditions.push({ metric: "clicks", operator: ">", value: 1 });
}

function handleDaysChange(val: string | number, which: "start" | "end") {
  const num = Number(String(val).replace(/天$/, ""));
  if (!isNaN(num) && num >= 0) {
    if (which === "start") form.effectiveDaysStart = num;
    else form.effectiveDaysEnd = num;
  }
}
function handleCondDaysChange(cSet: { days: number }, val: string | number) {
  const str = String(val).replace(/天$/, "");
  // "生命周期" 直接用 0
  if (str === "生命周期" || Number(str) === 0) {
    cSet.days = 0;
    return;
  }
  const num = Number(str);
  if (!isNaN(num) && num > 0) cSet.days = num;
}
function isPercentMetric(m: string) {
  return ["acos", "ctr", "cvr", "spendsPercent", "adsSalesPercent"].includes(m);
}

function open(data?: Partial<RuleFormData> | null, readonly: boolean = false): void {
  Object.assign(form, createEmptyForm());
  shopSearch.value = "";
  isEdit.value = false;
  isReadonly.value = readonly;
  if (data) {
    isEdit.value = true;
    const raw = JSON.parse(JSON.stringify(data));
    raw.conditionSets?.forEach((cs: any) =>
      cs.conditions?.forEach((c: any) => {
        if (c.isRange == null) c.isRange = !!c.value2;
      })
    );
    raw.targetingBidActions?.forEach((t: any) => {
      t._showConds = false;
    });
    Object.assign(form, raw);
  }
  visible.value = true;
  loadOptions();
}
function handleClose() {
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
  max-height: 68vh;
  padding-right: 12px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 4px;
  }

  :deep(.el-divider) {
    margin: 28px 0 20px;

    .el-divider__text {
      padding: 0 16px;
      font-size: 14px;
      font-weight: 700;
      color: #303133;
      letter-spacing: 0.3px;
      background: #fff;
    }
  }

  :deep(.el-form-item) {
    margin-bottom: 22px;
  }

  :deep(.el-form-item__label) {
    font-size: 13px;
    font-weight: 600;
    line-height: 32px;
    color: #374151;
  }

  :deep(.el-input__wrapper) {
    border-radius: 8px;
    transition:
      box-shadow 0.2s,
      border-color 0.2s;
  }

  :deep(.el-select .el-input__wrapper.is-focus) {
    box-shadow: 0 0 0 1px #409eff inset;
  }

  :deep(.el-input-number .el-input__wrapper.is-focus) {
    box-shadow: 0 0 0 1px #409eff inset;
  }
}

// 生效周期
.effective-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.fx-label,
.fx-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.fx-sep {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.effective-date-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.date-sep {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.effective-date-hint {
  margin-left: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

// 通用
.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.field-setting-row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.comparison-radios {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.targeting-sub-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
  padding: 16px 20px;
  margin-top: 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 10px;
}

.comparison-checkboxes {
  display: flex;
  gap: 16px;
}

.rule-relation-alert {
  margin: 8px 0 4px;

  :deep(.el-alert__title) {
    font-size: 13px;
  }

  p {
    margin: 2px 0;
    font-size: 12px;
    line-height: 1.6;
  }
}

.mb-4 {
  margin-bottom: 16px;
}

// 条件组
.condition-sets {
  margin-top: 10px;
}

.condition-set-card {
  position: relative;
  padding: 20px 24px;
  margin-bottom: 14px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition:
    border-color 0.25s,
    box-shadow 0.25s;

  &:hover {
    border-color: var(--el-color-primary-light-6);
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.1);
  }

  &::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    content: "";
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px 0 0 12px;
  }
}

.condition-set-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
}

.condition-set-label {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.condition-set-days {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 6px;
}

.condition-target-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.days-suffix {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
  white-space: nowrap;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.condition-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  transition: border-color 0.2s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }
}

.range-placeholder {
  min-width: 20px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.range-var {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.conflict-alert {
  margin-top: 6px;

  :deep(.el-alert__title) {
    font-size: 12px;
  }
}

.add-set-btn {
  margin-top: 4px;
}

.input-suffix {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

// 投放竞价操作
.tba-section {
  margin-bottom: 18px;
}

.tba-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.tba-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.tba-card {
  position: relative;
  padding: 20px 24px;
  margin-bottom: 14px;
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.03) 0%, rgba(16, 185, 129, 0.03) 100%);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);

  &::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    content: "";
    background: linear-gradient(180deg, #67c23a 0%, #10b981 100%);
    border-radius: 12px 0 0 12px;
  }
}

.tba-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.tba-card-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tba-card-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.tba-conditions {
  padding: 12px 16px;
  margin: 8px 0;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.tba-condition-set {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);

  &:last-child {
    border-bottom: none;
  }
}

.tba-cs-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

// 执行操作
.action-single-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.action-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.action-limit-label {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

// 关键词面板
.keyword-add-panel {
  padding: 18px 22px;
  margin-top: 12px;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.05) 0%, rgba(245, 158, 11, 0.05) 100%);
  border: 1px solid var(--el-color-warning-light-6);
  border-radius: 10px;
}

.kadd-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;

  &:last-child {
    margin-bottom: 0;
  }
}

.kadd-label {
  flex-shrink: 0;
  width: 72px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
