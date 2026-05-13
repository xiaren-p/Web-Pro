<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="900px"
    top="40px"
    :close-on-click-modal="false"
  >
    <div class="scrollable-form-content">
      <div class="tips-bar">
        <div>
          1. 时间都是站点时间，
          <span class="orange">美国使用美西时间</span>
          ；
        </div>
        <div>
          2. 合理安排权重，
          <span class="orange">广告分时策略规则只能命中一次</span>
          ；
        </div>
      </div>
      <el-form :model="form" label-width="100px" class="form-main">
        <el-form-item label="模板名称">
          <el-input
            v-model="form.name"
            maxlength="50"
            show-word-limit
            placeholder="50个字以内"
            style="width: 350px"
          />
        </el-form-item>
        <el-form-item label="适用店铺">
          <el-select v-model="form.shop" placeholder="请选择" style="width: 220px">
            <el-option label="请选择" value="" />
            <el-option label="美国" value="US" />
            <el-option label="英国" value="UK" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板状态">
          <el-radio-group v-model="form.status">
            <el-radio value="active" label="active">启用</el-radio>
            <el-radio value="inactive" label="inactive">暂停</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生效时间">
          <el-date-picker
            v-model="form.effectiveTime"
            type="daterange"
            start-placeholder="请选择开始时间"
            end-placeholder="请选择结束时间"
            style="width: 350px"
          />
        </el-form-item>
        <el-form-item label="基准值">
          <el-radio-group v-model="form.baseValueType">
            <el-radio value="apply" label="apply">应用策略时的值</el-radio>
            <el-radio value="fixed" label="fixed">
              固定值
              <el-input-number
                v-if="form.baseValueType === 'fixed'"
                v-model="form.baseFixedValue"
                size="small"
                :controls="false"
                style="width: 100px; margin-left: 8px"
                placeholder="0.02"
              />
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="字段设置">
          <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; width: 100%">
            <el-select
              v-model="form.category"
              placeholder="请选择归类"
              size="small"
              style="width: 140px"
            >
              <el-option label="主推款" value="main" />
              <el-option label="利润款" value="profit" />
              <el-option label="清仓款" value="clearance" />
            </el-select>
            <el-select
              v-model="form.managers"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择负责人"
              size="small"
              style="width: 150px"
            >
              <el-option label="张三" value="zhangsan" />
              <el-option label="李四" value="lisi" />
              <el-option label="当前系统" value="system" />
            </el-select>
            <el-select
              v-model="form.tags"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择标签"
              size="small"
              style="width: 150px"
            >
              <el-option label="爆款" value="hot" />
              <el-option label="清仓" value="clearance" />
              <el-option label="拉新" value="new" />
              <el-option label="活动" value="campaign" />
            </el-select>
          </div>
        </el-form-item>
        <el-form-item label="分时设置" class="time-setting-item">
          <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; width: 100%">
            <el-radio-group v-model="form.mode">
              <el-radio value="byDay" label="byDay">按天</el-radio>
              <el-radio value="byWeek" label="byWeek">按周</el-radio>
              <el-radio value="calendar" label="calendar">日历模式</el-radio>
            </el-radio-group>
            <span
              class="desc orange-star"
              style="margin-left: 4px; font-size: 12px; color: #f5a623"
            >
              * 时间都是指站点时间，美国使用美西时间
            </span>
          </div>
        </el-form-item>
        <el-form-item label-width="0" class="grid-form-item">
          <div v-show="form.mode === 'calendar'" class="time-grid-wrapper">
            <div class="time-grid-header">
              <div class="header-left">星期\时间</div>
              <div class="header-right">
                <div class="time-groups">
                  <div class="time-group">00:00 - 06:00</div>
                  <div class="time-group">06:00 - 12:00</div>
                  <div class="time-group">12:00 - 18:00</div>
                  <div class="time-group" style="border-right: none">18:00 - 24:00</div>
                </div>
                <div class="time-hours">
                  <span v-for="h in 24" :key="h" class="col-hour">{{ h - 1 }}</span>
                </div>
              </div>
            </div>
            <div class="time-grid-body" @mouseleave="onMouseLeaveGrid">
              <div v-for="(row, i) in weekRows" :key="i" class="time-grid-row">
                <div class="row-label">{{ row }}</div>
                <div class="row-cells">
                  <span
                    v-for="h in 24"
                    :key="h"
                    class="cell"
                    :class="getCellClass(i, h)"
                    :style="getCellBgStyle(i, h)"
                    @mousedown.prevent="onMouseDown(i, h)"
                    @mouseenter="onMouseEnter(i, h)"
                    @mouseup.stop="onMouseUp(i, h)"
                  >
                    <span class="cell-text" :style="getCellTextStyle(i, h)">
                      {{ getCellText(i, h) }}
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div v-show="form.mode === 'calendar'" class="grid-tools">
            <el-button style="height: auto; padding: 5px 15px" @click="clearGrid">清空</el-button>
            <div class="grid-tips">
              <el-icon
                color="#f5a623"
                style="margin-right: 4px; font-size: 14px; vertical-align: -2px"
              >
                <WarningFilled />
              </el-icon>
              <span class="orange">未设置的时段默认使用基准值</span>
              <span style="margin-left: 12px; font-size: 13px; color: #666">
                可以拖拽鼠标选择投放时间段
              </span>
            </div>
          </div>

          <div v-show="form.mode !== 'calendar'" class="time-segments-container">
            <div v-for="(seg, idx) in form.timeSegments" :key="idx" class="time-segment-row">
              <el-select
                v-if="form.mode === 'byWeek'"
                v-model="seg.dayOfWeek"
                size="small"
                style="width: 90px; margin-right: 8px"
              >
                <el-option label="周一" value="1" />
                <el-option label="周二" value="2" />
                <el-option label="周三" value="3" />
                <el-option label="周四" value="4" />
                <el-option label="周五" value="5" />
                <el-option label="周六" value="6" />
                <el-option label="周日" value="7" />
              </el-select>
              <el-time-select
                v-model="seg.startTime"
                start="00:00"
                step="01:00"
                end="24:00"
                placeholder="1:00"
                style="width: 90px"
                size="small"
              />
              <span class="tilde">~</span>
              <el-time-select
                v-model="seg.endTime"
                start="00:00"
                step="01:00"
                end="24:00"
                placeholder="6:00"
                style="width: 90px"
                size="small"
              />
              <el-select
                v-model="seg.operateType"
                size="small"
                style="width: 190px; margin-left: 12px"
              >
                <el-option label="在基准值上按百分比降低" value="percent_decrease" />
                <el-option label="在基准值上按百分比提高" value="percent_increase" />
                <el-option label="在基准值上按固定值增量" value="fixed_increase" />
                <el-option label="在基准值上按固定值减量" value="fixed_decrease" />
                <el-option label="使用固定值" value="fixed" />
              </el-select>
              <el-input-number
                v-model="seg.operateValue"
                size="small"
                :controls="false"
                style="width: 70px; margin-left: 12px"
              />
              <template v-if="seg.operateType === 'percent_decrease'">
                <span class="text">%，降低后，最低不低于</span>
                <el-input-number
                  v-model="seg.limitValue"
                  size="small"
                  :controls="false"
                  style="width: 70px; margin: 0 8px"
                />
                <span class="text">€</span>
              </template>
              <template v-else-if="seg.operateType === 'percent_increase'">
                <span class="text">%，提高后，最高不超过</span>
                <el-input-number
                  v-model="seg.limitValue"
                  size="small"
                  :controls="false"
                  style="width: 70px; margin: 0 8px"
                />
                <span class="text">€</span>
              </template>
              <template v-else-if="seg.operateType === 'fixed_decrease'">
                <span class="text">€，降低后，最低不低于</span>
                <el-input-number
                  v-model="seg.limitValue"
                  size="small"
                  :controls="false"
                  style="width: 70px; margin: 0 8px"
                />
                <span class="text">€</span>
              </template>
              <template v-else-if="seg.operateType === 'fixed_increase'">
                <span class="text">€，提高后，最高不超过</span>
                <el-input-number
                  v-model="seg.limitValue"
                  size="small"
                  :controls="false"
                  style="width: 70px; margin: 0 8px"
                />
                <span class="text">€</span>
              </template>
              <template v-else-if="seg.operateType === 'fixed'">
                <span class="text" style="margin-left: 8px">€</span>
              </template>
              <el-button
                v-if="form.timeSegments.length > 1"
                link
                type="danger"
                style="margin-left: 8px"
                @click="removeSegment(idx)"
              >
                删除
              </el-button>
            </div>
            <div class="segment-tools">
              <el-button style="height: auto; padding: 5px 15px" @click="addSegment">
                +添加时间段
              </el-button>
              <div class="grid-tips" style="margin-left: 20px">
                <el-icon
                  color="#f5a623"
                  style="margin-right: 4px; font-size: 14px; vertical-align: -2px"
                >
                  <WarningFilled />
                </el-icon>
                <span class="orange">未设置的时段默认使用基准价</span>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="失效回调" class="callback-form-item">
          <div class="callback-container">
            <div class="callback-desc">
              模板生效时间结束、模板暂停或取消应用模板时，将每个对象的竞价调整为
            </div>
            <el-radio-group v-model="form.invalidCallbackType" class="callback-radios">
              <el-radio value="multiplier" label="multiplier" style="margin-right: 16px">
                基准价 x
                <el-input-number
                  v-model="form.invalidCallbackMultiplier"
                  :controls="false"
                  style="width: 80px; margin-left: 8px"
                  size="small"
                />
              </el-radio>
              <el-radio value="fixed" label="fixed" style="margin-right: 16px">
                固定值: €
                <el-input-number
                  v-model="form.invalidCallbackFixed"
                  :controls="false"
                  style="width: 80px; margin-left: 8px"
                  size="small"
                />
              </el-radio>
              <el-radio value="previous" label="previous" style="margin-right: 16px">
                应用策略前的竞价
              </el-radio>
              <el-radio value="none" label="none">不回调</el-radio>
            </el-radio-group>
          </div>
        </el-form-item>

        <el-form-item label="权重">
          <div style="display: flex; align-items: center">
            <el-input-number
              v-model="form.weight"
              :min="1"
              :precision="0"
              :controls="false"
              placeholder="请输入数值"
              style="width: 150px"
            />
            <span class="orange" style="margin-left: 14px; font-size: 13px">
              权重越高广告规则命中的优先级越高
            </span>
          </div>
        </el-form-item>

        <el-form-item label="执行结果" style="margin-bottom: 0">
          <el-select v-model="form.executionResult" style="width: 220px">
            <el-option label="不通知" value="no_notice" />
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button type="primary" @click="onSubmit">保存</el-button>
    </template>

    <!-- 竞价策略配置弹窗 -->
    <el-dialog
      v-model="strategyDialogVisible"
      title="设置竞价策略"
      width="450px"
      append-to-body
      :close-on-click-modal="false"
    >
      <template #header="{ titleId, titleClass }">
        <div
          style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-right: 20px;
          "
        >
          <span :id="titleId" :class="titleClass">设置竞价策略</span>
          <el-button link type="primary" @click="clearSelectionSettings">清空设置</el-button>
        </div>
      </template>
      <el-form label-width="90px">
        <el-form-item label="时间段:">
          <div style="padding-top: 6px; line-height: normal">
            <div style="color: #333">{{ displaySelectionDays }}</div>
            <div style="margin-top: 4px; color: #666">{{ displaySelectionHours }}</div>
          </div>
        </el-form-item>
        <el-form-item label="竞价策略:">
          <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 4px">
            <el-select v-model="strategyForm.operateType" size="small" style="width: 220px">
              <el-option label="在基准值上按百分比降低" value="percent_decrease" />
              <el-option label="在基准值上按百分比提高" value="percent_increase" />
              <el-option label="在基准值上按固定值增量" value="fixed_increase" />
              <el-option label="在基准值上按固定值减量" value="fixed_decrease" />
              <el-option label="使用固定值" value="fixed" />
            </el-select>
            <div style="display: flex; flex-wrap: wrap; align-items: center">
              <el-input-number
                v-model="strategyForm.operateValue"
                :controls="false"
                size="small"
                style="width: 70px"
              />
              <template v-if="strategyForm.operateType === 'percent_decrease'">
                <span class="text" style="margin: 0 8px; font-size: 13px; color: #333">
                  %，降低后最低不低于
                </span>
                <el-input-number
                  v-model="strategyForm.limitValue"
                  :controls="false"
                  size="small"
                  style="width: 70px"
                />
                <span class="text" style="margin-left: 8px; font-size: 13px; color: #333">€</span>
              </template>
              <template v-else-if="strategyForm.operateType === 'percent_increase'">
                <span class="text" style="margin: 0 8px; font-size: 13px; color: #333">
                  %，提高后最高不超过
                </span>
                <el-input-number
                  v-model="strategyForm.limitValue"
                  :controls="false"
                  size="small"
                  style="width: 70px"
                />
                <span class="text" style="margin-left: 8px; font-size: 13px; color: #333">€</span>
              </template>
              <template v-else-if="strategyForm.operateType === 'fixed_decrease'">
                <span class="text" style="margin: 0 8px; font-size: 13px; color: #333">
                  €，降低后最低不低于
                </span>
                <el-input-number
                  v-model="strategyForm.limitValue"
                  :controls="false"
                  size="small"
                  style="width: 70px"
                />
                <span class="text" style="margin-left: 8px; font-size: 13px; color: #333">€</span>
              </template>
              <template v-else-if="strategyForm.operateType === 'fixed_increase'">
                <span class="text" style="margin: 0 8px; font-size: 13px; color: #333">
                  €，提高后最高不超过
                </span>
                <el-input-number
                  v-model="strategyForm.limitValue"
                  :controls="false"
                  size="small"
                  style="width: 70px"
                />
                <span class="text" style="margin-left: 8px; font-size: 13px; color: #333">€</span>
              </template>
              <template v-else-if="strategyForm.operateType === 'fixed'">
                <span class="text" style="margin-left: 8px; font-size: 13px; color: #333">€</span>
              </template>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="strategyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmStrategy">确定</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import { WarningFilled } from "@element-plus/icons-vue";

const visible = ref(false);
const dialogTitle = ref("创建分时调竞价策略");

const form = reactive({
  name: "",
  shop: "",
  status: "active",
  effectiveTime: [],
  baseValueType: "apply",
  baseFixedValue: null as number | null,
  category: "",
  managers: [],
  tags: [],
  weight: 1,
  mode: "byDay",
  grid: Array(7)
    .fill(0)
    .map(() => Array(24).fill(null as any)),
  timeSegments: [
    {
      dayOfWeek: "1",
      startTime: "01:00",
      endTime: "06:00",
      operateType: "percent_decrease",
      operateValue: 0.02,
      limitValue: 0.02,
    },
  ],
  invalidCallbackType: "previous",
  invalidCallbackMultiplier: 1.0 as number | null,
  invalidCallbackFixed: null as number | null,
  executionResult: "no_notice",
});

const weekRows = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

// ---- 日历拖拽逻辑 ----
const isDragging = ref(false);
const dragStart = ref({ r: -1, c: -1 });
const dragEnd = ref({ r: -1, c: -1 });

const nextGroupId = ref(1);
const editingGroupId = ref<number | null>(null);
const pastelColors = [
  "#f89898",
  "#b3e19d",
  "#a0cfff",
  "#f3d19e",
  "#d4b3ff",
  "#ffb6c1",
  "#87ceeb",
  "#ffe4b5",
  "#98fb98",
  "#e6e6fa",
  "#ffdab9",
  "#afeeee",
  "#ff9fe1",
  "#fcf0a4",
  "#a1f4a9",
];

const strategyDialogVisible = ref(false);
const currentSelection = ref({ minR: -1, maxR: -1, minC: -1, maxC: -1 });
const strategyForm = reactive({
  operateType: "percent_increase",
  operateValue: null as number | null,
  limitValue: null as number | null,
});

const strategyLabels: Record<string, string> = {
  percent_increase: "提(%)",
  fixed_increase: "提(值)",
  percent_decrease: "降(%)",
  fixed_decrease: "降(值)",
  fixed: "固定值",
};

const displaySelectionDays = computed(() => {
  const { minR, maxR } = currentSelection.value;
  if (minR === -1) return "";
  if (minR === maxR) return weekRows[minR];
  return `${weekRows[minR]} - ${weekRows[maxR]}`;
});

const displaySelectionHours = computed(() => {
  const { minC, maxC } = currentSelection.value;
  if (minC === -1) return "";
  return `${minC}:00 - ${maxC + 1}:00`;
});

function getCellClass(r: number, h: number) {
  const c = h - 1;
  const classes = [];
  const cellData = form.grid[r][c];

  if (isDragging.value && dragStart.value.r >= 0 && dragStart.value.c >= 0) {
    const startCell = form.grid[dragStart.value.r][dragStart.value.c];
    if (startCell && startCell.groupId != null) {
      // 拖拽起始于已有组时，高亮整个组
      if (cellData && cellData.groupId === startCell.groupId) {
        classes.push("cell-dragging");
      }
    } else {
      // 新拖拽时，高亮选区
      const minR = Math.min(dragStart.value.r, dragEnd.value.r);
      const maxR = Math.max(dragStart.value.r, dragEnd.value.r);
      const minC = Math.min(dragStart.value.c, dragEnd.value.c);
      const maxC = Math.max(dragStart.value.c, dragEnd.value.c);
      if (r >= minR && r <= maxR && c >= minC && c <= maxC) {
        classes.push("cell-dragging");
      }
    }
  }

  if (cellData) {
    if (c < 23 && form.grid[r][c + 1] && form.grid[r][c + 1].groupId === cellData.groupId) {
      classes.push("cell-merged-right");
    }
  }
  return classes.join(" ");
}

function getCellBgStyle(r: number, h: number) {
  const c = h - 1;
  const cellData = form.grid[r][c];
  if (cellData && cellData.color) {
    return { backgroundColor: cellData.color };
  }
  return {};
}

function getCellText(r: number, h: number) {
  const c = h - 1;
  const cellData = form.grid[r][c];
  if (!cellData) return "";
  // 只在每段连续策略的最左侧展示文字
  if (c === 0 || form.grid[r][c - 1]?.groupId !== cellData.groupId) {
    const label = strategyLabels[cellData.type] || "";
    const val = cellData.operateValue ? ` ${cellData.operateValue}` : "";
    return label + val;
  }
  return "";
}

function getCellTextStyle(r: number, h: number): any {
  const c = h - 1;
  const cellData = form.grid[r][c];
  if (!cellData) return { display: "none" };

  if (c === 0 || form.grid[r][c - 1]?.groupId !== cellData.groupId) {
    let span = 1;
    for (let nextC = c + 1; nextC < 24; nextC++) {
      if (form.grid[r][nextC]?.groupId === cellData.groupId) {
        span++;
      } else {
        break;
      }
    }
    return {
      position: "absolute",
      left: 0,
      top: 0,
      bottom: 0,
      width: `calc(100% * ${span})`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1,
      pointerEvents: "none",
      color: "#333",
      fontWeight: 500,
    };
  }
  return { display: "none" };
}

function onMouseDown(r: number, h: number) {
  isDragging.value = true;
  dragStart.value = { r, c: h - 1 };
  dragEnd.value = { r, c: h - 1 };
}

function onMouseEnter(r: number, h: number) {
  if (isDragging.value) {
    dragEnd.value = { r, c: h - 1 };
  }
}

function onMouseUp(r: number, h: number) {
  if (isDragging.value) {
    dragEnd.value = { r, c: h - 1 };
    finishDrag();
  }
}

function onMouseLeaveGrid() {
  if (isDragging.value) {
    finishDrag();
  }
}

function finishDrag() {
  if (dragStart.value.r === -1 || dragStart.value.c === -1) {
    isDragging.value = false;
    return;
  }
  isDragging.value = false;
  const startCell = form.grid[dragStart.value.r][dragStart.value.c];

  if (startCell && startCell.groupId != null) {
    // 操作已有分块
    const targetGroupId = startCell.groupId;
    editingGroupId.value = targetGroupId;

    let minR = 7,
      maxR = -1,
      minC = 24,
      maxC = -1;
    for (let r = 0; r < 7; r++) {
      for (let c = 0; c < 24; c++) {
        if (form.grid[r][c]?.groupId === targetGroupId) {
          minR = Math.min(minR, r);
          maxR = Math.max(maxR, r);
          minC = Math.min(minC, c);
          maxC = Math.max(maxC, c);
        }
      }
    }
    currentSelection.value = { minR, maxR, minC, maxC };
    strategyForm.operateType = startCell.operateType || "percent_increase";
    strategyForm.operateValue = startCell.operateValue || "";
    strategyForm.limitValue = startCell.limitValue || "";
  } else {
    // 新建分块
    editingGroupId.value = null;
    currentSelection.value = {
      minR: Math.min(dragStart.value.r, dragEnd.value.r),
      maxR: Math.max(dragStart.value.r, dragEnd.value.r),
      minC: Math.min(dragStart.value.c, dragEnd.value.c),
      maxC: Math.max(dragStart.value.c, dragEnd.value.c),
    };
    strategyForm.operateType = "percent_increase";
    strategyForm.operateValue = null;
    strategyForm.limitValue = null;
  }

  strategyDialogVisible.value = true;
}

function clearSelectionSettings() {
  if (editingGroupId.value != null) {
    // 清除整个已存在的组
    for (let r = 0; r < 7; r++) {
      for (let c = 0; c < 24; c++) {
        if (form.grid[r][c]?.groupId === editingGroupId.value) {
          form.grid[r][c] = null;
        }
      }
    }
  } else {
    // 清除新拖拽的范围
    const { minR, maxR, minC, maxC } = currentSelection.value;
    for (let r = minR; r <= maxR; r++) {
      for (let c = minC; c <= maxC; c++) {
        form.grid[r][c] = null;
      }
    }
  }
  strategyDialogVisible.value = false;
  editingGroupId.value = null;
}

function confirmStrategy() {
  if (editingGroupId.value != null) {
    // 修改已存在的组（仅改变策略内容）
    for (let r = 0; r < 7; r++) {
      for (let c = 0; c < 24; c++) {
        if (form.grid[r][c]?.groupId === editingGroupId.value) {
          form.grid[r][c].type = strategyForm.operateType;
          form.grid[r][c].operateValue = strategyForm.operateValue;
          form.grid[r][c].limitValue = strategyForm.limitValue;
        }
      }
    }
  } else {
    // 创建新组
    const { minR, maxR, minC, maxC } = currentSelection.value;
    const groupId = nextGroupId.value++;
    const color = pastelColors[(groupId - 1) % pastelColors.length];

    for (let r = minR; r <= maxR; r++) {
      for (let c = minC; c <= maxC; c++) {
        form.grid[r][c] = {
          type: strategyForm.operateType,
          operateValue: strategyForm.operateValue,
          limitValue: strategyForm.limitValue,
          groupId,
          color,
        };
      }
    }
  }
  strategyDialogVisible.value = false;
  editingGroupId.value = null;
}

function clearGrid() {
  form.grid = Array(7)
    .fill(0)
    .map(() => Array(24).fill(null));
}
function addSegment() {
  form.timeSegments.push({
    dayOfWeek: "1",
    startTime: "",
    endTime: "",
    operateType: "percent_decrease",
    operateValue: 0,
    limitValue: 0,
  });
}
function removeSegment(index: number) {
  form.timeSegments.splice(index, 1);
}
function onCancel() {
  visible.value = false;
}
function onSubmit() {
  // TODO: 校验并提交
  visible.value = false;
}

// 暴露方法用于外部控制弹窗显示
function open() {
  visible.value = true;
}
defineExpose({ open });
</script>

<style scoped lang="scss" src="./BiddingStrategyForm.scss"></style>
