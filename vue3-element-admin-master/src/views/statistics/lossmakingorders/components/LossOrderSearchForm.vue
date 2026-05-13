<template>
  <div class="search-container">
    <el-form ref="queryFormRef" :model="filters" :inline="true">
      <el-form-item label="店铺">
        <el-select
          v-model="filters.shops"
          multiple
          placeholder="请选择店铺"
          style="min-width: 120px"
        >
          <el-option v-if="shops.length" label="全选" :value="ALL_SHOPS_VALUE" />
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
          <el-option v-if="owners.length" label="全选" :value="ALL_OWNERS_VALUE" />
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
        />
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
</template>

<script setup lang="ts">
/**
 * 亏损订单搜索栏：纯展示组件，仅负责渲染表单与本地交互。
 * - 通过 v-model:filters 双向绑定页面层的筛选模型
 * - 通过 emit('query') / emit('reset') 通知页面重新加载或重置
 * 所属板块：statistics / lossmakingOrders。
 */
import { ref } from "vue";
import { ElMessage } from "element-plus";

import {
  ALL_SHOPS_VALUE,
  ALL_OWNERS_VALUE,
  currencies,
  ruleDescription,
} from "@/composables/lossmakingOrders/useLossOrderHelpers";
import type { LossOrderFilters } from "@/composables/lossmakingOrders/useLossOrderQuery";

interface ShopOption {
  label: string;
  value: string;
  country?: string;
}
interface OwnerOption {
  label: string;
  value: string;
}

const props = defineProps<{
  filters: LossOrderFilters;
  shops: ShopOption[];
  owners: OwnerOption[];
  dateShortcuts: any[];
}>();

const emit = defineEmits<{
  (e: "query"): void;
  (e: "reset"): void;
}>();

const queryFormRef = ref();

/** MSKU 多行弹窗状态。 */
const mskuPopoverText = ref("");
const mskuPopoverVisible = ref(false);

function openMskuPopover() {
  mskuPopoverText.value = props.filters.msku || "";
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
      props.filters.msku = lines.slice(0, 2000).join("\n");
    } else {
      props.filters.msku = lines.join("\n");
    }
    mskuPopoverVisible.value = false;
    emit("query");
  } catch (e) {
    console.error("applyMskuSearch error", e);
    ElMessage.error("搜索失败");
  }
}

function handleQuery() {
  emit("query");
}

function handleReset() {
  queryFormRef.value?.resetFields?.();
  emit("reset");
}

defineExpose({ queryFormRef });
</script>

<style scoped lang="scss">
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

/* popover textarea & buttons */
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
.popover-advanced-input .el-button {
  min-height: 26px;
  padding: 4px 8px;
  font-size: 11px;
}
.popover-advanced-input .el-button--mini {
  min-height: 24px;
  padding: 2px 6px;
}
.popover-advanced-input .el-button,
.popover-advanced-input .el-button.is-round,
.popover-advanced-input .el-button--mini.is-round {
  border-radius: 6px !important;
}
</style>
