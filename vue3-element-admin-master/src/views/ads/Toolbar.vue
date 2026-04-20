<template>
  <div
    class="col-sm-12 flex-panel lay-left-center search-line"
    style="position: relative; float: none; min-height: 40px"
  >
    <div class="input-group" style="display: flex; align-items: center">
      <template v-if="showLeftControls">
        <div style="position: relative">
          <a class="btn btn-info" href="javascript:;" @click.prevent="$emit('toggle-create')">
            + 创建广告活动
            <span class="caret"></span>
          </a>
          <ul
            v-show="showCreateDropdown"
            class="dropdown-menu"
            style="position: absolute; left: 0; z-index: 20; display: block; margin-top: 6px"
          >
            <li>
              <a href="#" @click.prevent="$emit('jump', '/ad_report/campaign/generate/index')">
                创建SP广告
              </a>
            </li>
            <li>
              <a href="#" @click.prevent="$emit('jump', '/ad_report/headline/generate/create')">
                创建SB广告
              </a>
            </li>
            <li>
              <a href="#" @click.prevent="$emit('jump', '/ad_report/sd/generate/index')">
                创建SD广告
              </a>
            </li>
          </ul>
        </div>
        <div class="input-group" style="margin-left: 8px">
          <a
            class="btn super-structrue"
            href="#"
            title="使用超级结构，可批量创建广告活动和添加关键词，效率提升80%！"
            @click.prevent="$emit('open-super-structure')"
          >
            批量建广告
          </a>
        </div>
      </template>

      <div
        v-if="showRightControls"
        class="input-group top-right-line"
        style="position: absolute; right: 0"
      >
        <span class="m-r-20 col-grey font-12 new-report-time">
          <span class="time-text">报告更新(西班牙)：04/09 04:53</span>
          <span
            class="caret m-l-5"
            style="transform: rotate(0deg)"
            @click.prevent="$emit('toggle-report-time-list')"
          ></span>
          <div
            v-show="showReportTimeList"
            class="show-report-time-list"
            style="
              position: absolute;
              right: 0;
              z-index: 30;
              width: 320px;
              padding: 8px;
              background: #fff;
              border: 1px solid #eee;
            "
          >
            <div class="show-report-time-contaign" style="max-height: 260px; overflow: auto">
              <div
                v-for="(item, idx) in reportTimes"
                :key="idx"
                class="show-report-time-item"
                style="padding: 6px 0; border-bottom: 1px solid #f5f5f5"
              >
                <span class="show-report-time-text">
                  <span class="oneLine">{{ item.profile }}</span>
                  <span class="m-l-5">{{ item.country }}</span>
                  ：
                  <span>{{ item.time }}</span>
                </span>
              </div>
            </div>
          </div>
        </span>

        <div
          class="inl-blk-mid"
          style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-left: 8px;
          "
        >
          <label style="margin-bottom: 0">
            <input
              id="OnlyOverBudget"
              class="form-control filled-in chk-col-blue"
              type="checkbox"
              :checked="onlyOverBudget"
              @change="$emit('update:only-over-budget', $event.target.checked)"
            />
            <span style="margin-left: 6px">只查看超预算的</span>
          </label>
        </div>
        <div
          class="inl-blk-mid"
          style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-left: 8px;
          "
        >
          <label style="margin-bottom: 0">
            <input
              id="WithRing2"
              class="form-control filled-in chk-col-blue"
              type="checkbox"
              :checked="withRing"
              @change="$emit('update:with-ring', $event.target.checked)"
            />
            <span style="padding-right: 5px; margin-left: 6px">
              <span class="ring-label-text">环比</span>
            </span>
          </label>
          <i
            class="fa fa-edit font-12"
            style="margin-left: 6px; cursor: pointer"
            @click.prevent="$emit('toggle-ring-date')"
          ></i>
          <div
            v-show="showRingDate"
            style="position: relative; display: inline-block; margin-left: 8px"
          >
            <el-date-picker
              v-model="innerRingDateRange"
              type="daterange"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              unlink-panels
              style="width: 205px"
              @change="$emit('ring-date-change', innerRingDateRange)"
            />
            <i
              class="fa fa-input_clear font-12"
              style="position: absolute; top: 8px; right: 6px; cursor: pointer"
              @click.prevent="$emit('ring-date-change', [])"
            ></i>
          </div>
        </div>
        <div class="inl-blk-mid" style="margin-left: 8px">
          <button
            class="btn btn-default Js-show-compare-warn waves-effect"
            @click.prevent="$emit('show-compare-warn')"
          >
            对比预警
          </button>
        </div>
        <button
          class="btn btn-default Js-show-dt-top-chart waves-effect"
          style="margin-left: 8px"
          data-state="1"
          @click.prevent="$emit('toggle-chart')"
        >
          隐藏图表
          <i class="fa fa-close_visible m-l-5 font-14"></i>
        </button>
        <div class="btn-group set-columns" style="position: relative; margin-left: 8px">
          <button
            type="button"
            class="btn dropdown-left btn-default more-columns"
            @click.prevent="$emit('restore-default-columns')"
          >
            列配置
          </button>
        </div>
        <a
          href="https://www.lingxing.com/CN-manual/article/Alladvertisingcampaigns"
          target="_blank"
          class="btn btn-default"
          style="padding: 5px 8px !important; margin-left: 8px"
        >
          <i class="font-16 fa fa-explain" style="top: 2px"></i>
        </a>
        <button
          id="DtExport"
          class="btn btn-default fa fa-download fa-btn waves-effect font-16"
          style="padding: 5px 8px !important; margin-left: 8px"
          @click.prevent="$emit('export-data')"
        ></button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

defineEmits([
  "toggle-create",
  "jump",
  "open-super-structure",
  "toggle-report-time-list",
  "update:only-over-budget",
  "update:with-ring",
  "toggle-ring-date",
  "ring-date-change",
  "show-compare-warn",
  "toggle-chart",
  "restore-default-columns",
  "export-data",
]);

const props = defineProps({
  reportTimes: { type: Array, default: () => [] },
  showCreateDropdown: { type: Boolean, default: false },
  showReportTimeList: { type: Boolean, default: false },
  onlyOverBudget: { type: Boolean, default: false },
  withRing: { type: Boolean, default: false },
  showRingDate: { type: Boolean, default: false },
  ringDateRange: { type: Array, default: () => [] },
  // control visibility of left/right parts so parent can avoid duplicate UI
  showLeftControls: { type: Boolean, default: true },
  showRightControls: { type: Boolean, default: true },
});

// local copy for el-date-picker v-model
const innerRingDateRange = ref(props.ringDateRange || []);
watch(
  () => props.ringDateRange,
  (v) => {
    innerRingDateRange.value = v || [];
  }
);
</script>

<style scoped lang="scss">
/* Toolbar-specific styles are in parent ads.scss */
</style>
