<template>
  <el-dialog
    v-model="visible"
    :title="step === 'form' ? '新建广告 · 文件上传' : '上传解析结果'"
    width="600px"
    align-center
    destroy-on-close
    @closed="handleReset"
  >
    <!-- ── 步骤一：上传表单 ── -->
    <div v-if="step === 'form'" class="upload-form">
      <!-- 文件级错误内联提示 -->
      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        closable
        style="margin-bottom: 16px"
        @close="errorMsg = ''"
      />

      <!-- 文件拖拽上传区 -->
      <el-upload
        ref="uploadRef"
        class="ad-upload-area"
        drag
        :auto-upload="false"
        accept=".xlsx"
        :limit="1"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :on-exceed="handleExceed"
      >
        <el-icon class="ad-upload-icon"><UploadFilled /></el-icon>
        <div class="ad-upload-text">
          将
          <b>.xlsx</b>
          文件拖拽至此，或
          <em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="ad-upload-tip">仅支持 .xlsx 格式 · 最大 20 MB</div>
        </template>
      </el-upload>


      <!-- 广告类型 -->
      <div class="upload-section">
        <div class="upload-section__title">广告类型</div>
        <el-radio-group v-model="adTypeFilter" class="ad-type-group">
          <el-radio-button value="all">都创建</el-radio-button>
          <el-radio-button value="auto">仅自动广告</el-radio-button>
          <el-radio-button value="manual">仅手动广告</el-radio-button>
        </el-radio-group>
        <div class="upload-section__desc">
          <template v-if="adTypeFilter === 'all'">
            自动广告与手动广告均创建（手动广告需填写关键词，否则跳过）
          </template>
          <template v-else-if="adTypeFilter === 'auto'">
            仅处理广告活动名以
            <code>AUTO</code>
            结尾的条目，MANU 条目全部忽略
          </template>
          <template v-else>
            仅处理广告活动名以
            <code>MANU</code>
            结尾且存在关键词的条目，AUTO 条目全部忽略
          </template>
        </div>
        
      </div>

      <!-- 投放国家 -->
      <div class="upload-section">
        <div class="upload-section__title">
          投放国家
          <el-switch
            v-model="useAutoSites"
            active-text="按表需求"
            inactive-text="手动指定"
            inline-prompt
            style="margin-left: 12px; vertical-align: middle"
            @change="handleAutoSitesChange"
          />
        </div>

        <transition name="slide-down">
          <div v-if="!useAutoSites" class="country-picker">
            <div class="country-grid">
              <div
                v-for="c in COUNTRY_OPTIONS"
                :key="c.value"
                class="country-card"
                :class="{ 'is-active': selectedCountries.includes(c.value) }"
                @click="toggleCountry(c.value)"
              >
                <span class="country-flag">{{ c.flag }}</span>
                <span class="country-code">{{ c.value }}</span>
              </div>
            </div>
            <div class="country-footer">
              <template v-if="selectedCountries.length > 0">
                <span class="country-selected">
                  已选 {{ selectedCountries.length }} 个：{{ selectedCountries.join("、") }}
                </span>
                <span class="country-muted">（文件中不存在的站点子表将自动忽略）</span>
              </template>
              <span v-else class="country-empty">请至少选择一个国家</span>
            </div>
          </div>
          <div v-else class="country-auto-tip">
            自动读取 Excel 中所有合规站点子表（子表名须为两位大写国家代码，如 DE、UK）
          </div>
        </transition>
      </div>

      <!-- 竞价设置 -->
      <div class="upload-section">
        <div class="upload-section__title">竞价设置</div>

        <!-- 第一行：每日预算 + 广告组默认竞价 -->
        <div class="bidding-grid bidding-grid--top">
          <div class="bidding-item">
            <span class="bidding-label">每日预算</span>
            <el-input-number
              v-model="dailyBudget"
              :min="0.01"
              :step="0.5"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
          <div class="bidding-item">
            <span class="bidding-label">广告组默认竞价</span>
            <el-input-number
              v-model="defaultBid"
              :min="0.01"
              :step="0.01"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
        </div>

        <!-- 自动定向组竞价：四列网格 -->
        <div class="bidding-sub-title">
          <span>自动定向组竞价</span>
        </div>
        <div class="bidding-grid bidding-grid--auto">
          <div class="bidding-item">
            <span class="bidding-label">紧密匹配</span>
            <el-input-number
              v-model="closeMatchBid"
              :min="0.01"
              :step="0.01"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
          <div class="bidding-item">
            <span class="bidding-label">同类匹配</span>
            <el-input-number
              v-model="looseMatchBid"
              :min="0.01"
              :step="0.01"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
          <div class="bidding-item">
            <span class="bidding-label">宽泛匹配</span>
            <el-input-number
              v-model="substitutesBid"
              :min="0.01"
              :step="0.01"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
          <div class="bidding-item">
            <span class="bidding-label">关联匹配</span>
            <el-input-number
              v-model="complementsBid"
              :min="0.01"
              :step="0.01"
              :precision="2"
              controls-position="right"
              class="bidding-input"
            />
          </div>
        </div>
      </div>
      <!-- 关键词匹配规则说明（表单底部） -->
      <el-alert
        type="info"
        show-icon
        :closable="false"
        style="margin-top: 6px"
        description="关键词匹配规则：单个单词（如 word、hello）或月搜索量大于 10000 时，采用精准匹配（exact）；其余情况采用宽泛匹配（broad)。"
      />

    </div>

    <!-- ── 步骤二：解析结果 ── -->
    <div v-else class="upload-result">
      <div class="upload-result__summary">
        <el-tag type="success" size="large" effect="dark">
          成功 {{ uploadResult!.success_count }} 条
        </el-tag>
        <el-tag
          v-if="uploadResult!.failed_count > 0"
          type="danger"
          size="large"
          effect="dark"
          style="margin-left: 12px"
        >
          失败 {{ uploadResult!.failed_count }} 条
        </el-tag>
        <el-tag
          v-if="uploadResult!.skipped_warnings.length > 0"
          type="warning"
          size="large"
          effect="dark"
          style="margin-left: 12px"
        >
          跳过 {{ uploadResult!.skipped_warnings.length }} 条
        </el-tag>
      </div>

      <template v-if="uploadResult!.failed_count > 0">
        <el-divider content-position="left">失败明细</el-divider>
        <el-table :data="failedRows" max-height="200" size="small" border>
          <el-table-column
            prop="campaign_name"
            label="广告活动"
            min-width="150"
            show-overflow-tooltip
          />
          <el-table-column prop="country" label="国家" width="68" align="center" />
          <el-table-column prop="ad_type_label" label="类型" width="68" align="center" />
          <el-table-column prop="msg" label="失败原因" min-width="150" show-overflow-tooltip />
        </el-table>
      </template>

      <template v-if="uploadResult!.skipped_warnings.length > 0">
        <el-divider content-position="left">跳过提示（不入队列）</el-divider>
        <ul class="upload-result__warnings">
          <li v-for="(w, i) in uploadResult!.skipped_warnings" :key="i">{{ w }}</li>
        </ul>
      </template>
    </div>

    <!-- ── 底部按钮 ── -->
    <template #footer>
      <template v-if="step === 'form'">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile || (!useAutoSites && selectedCountries.length === 0)"
          @click="handleSubmit"
        >
          开始上传
        </el-button>
      </template>
      <template v-else>
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="handleViewQueue">查看队列</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 新建广告上传对话框。
 * 提供拖拽上传 xlsx、广告类型筛选、投放国家选择功能；
 * 上传完成后在同一弹窗内内联展示解析结果（成功/失败/跳过汇总）。
 * 所属板块：ads。
 */
import type { UploadInstance, UploadFile, UploadRawFile } from "element-plus";
import type { AdUploadResponse } from "@/api/ads";

import { computed, ref, watch } from "vue";
import { genFileId } from "element-plus";
import { UploadFilled } from "@element-plus/icons-vue";

import { uploadAdXlsx } from "@/api/ads";

// ── 常量：支持的 Amazon 主流站点列表 ──────────────────────────────────────────
const COUNTRY_OPTIONS = [
  { value: "DE", flag: "🇩🇪" },
  { value: "UK", flag: "🇬🇧" },
  { value: "FR", flag: "🇫🇷" },
  { value: "IT", flag: "🇮🇹" },
  { value: "ES", flag: "🇪🇸" },
  { value: "NL", flag: "🇳🇱" },
  { value: "SE", flag: "🇸🇪" },
  { value: "PL", flag: "🇵🇱" },
  { value: "BE", flag: "🇧🇪" },
  { value: "US", flag: "🇺🇸" },
  { value: "CA", flag: "🇨🇦" },
  { value: "MX", flag: "🇲🇽" },
  { value: "BR", flag: "🇧🇷" },
  { value: "JP", flag: "🇯🇵" },
  { value: "AU", flag: "🇦🇺" },
  { value: "SA", flag: "🇸🇦" },
  { value: "AE", flag: "🇦🇪" },
  { value: "IN", flag: "🇮🇳" },
  { value: "SG", flag: "🇸🇬" },
  { value: "TR", flag: "🇹🇷" },
] as const;

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "view-queue"): void;
}>();

// ── 响应式状态 ─────────────────────────────────────────────────────────────────
const visible = ref(props.visible);
watch(
  () => props.visible,
  (val) => {
    visible.value = val;
  }
);
watch(visible, (val) => emit("update:visible", val));

const uploadRef = ref<UploadInstance | null>(null);
const selectedFile = ref<File | null>(null);
const uploading = ref(false);
const errorMsg = ref("");
const step = ref<"form" | "result">("form");
const uploadResult = ref<AdUploadResponse | null>(null);

const adTypeFilter = ref<"all" | "auto" | "manual">("all");
const useAutoSites = ref(true);
const selectedCountries = ref<string[]>([]);

// 竞价设置默认値
const dailyBudget = ref<number>(1);
const defaultBid = ref<number>(0.12);
const closeMatchBid = ref<number>(0.12);
const looseMatchBid = ref<number>(0.1);
const substitutesBid = ref<number>(0.1);
const complementsBid = ref<number>(0.1);

/** 失败记录列表（computed，供结果表格使用） */
const failedRows = computed(
  () => uploadResult.value?.list.filter((r) => r.parse_status === 0) ?? []
);

// ── 文件处理 ───────────────────────────────────────────────────────────────────

/**
 * 文件选择变更：更新 selectedFile。
 *
 * @param {UploadFile} file - element-plus 上传文件对象
 */
function handleFileChange(file: UploadFile): void {
  selectedFile.value = file.raw ?? null;
  errorMsg.value = "";
}

/**
 * 文件移除：清空 selectedFile。
 */
function handleFileRemove(): void {
  selectedFile.value = null;
}

/**
 * 超出文件数量限制：替换为新选择的文件。
 *
 * @param {File[]} files - 超出限制的文件列表
 */
function handleExceed(files: File[]): void {
  uploadRef.value?.clearFiles();
  const raw = files[0] as UploadRawFile;
  raw.uid = genFileId();
  uploadRef.value?.handleStart(raw);
  selectedFile.value = raw;
}

// ── 国家选择 ───────────────────────────────────────────────────────────────────

/**
 * 切换至"按表需求"时清空手动选择的国家列表。
 *
 * @param {boolean | string | number} val - switch 当前值
 */
function handleAutoSitesChange(val: boolean | string | number): void {
  if (val) {
    selectedCountries.value = [];
  }
}

/**
 * 点击国家卡片时切换选中状态。
 *
 * @param {string} code - 国家代码，如 "DE"
 */
function toggleCountry(code: string): void {
  const idx = selectedCountries.value.indexOf(code);
  if (idx >= 0) {
    selectedCountries.value.splice(idx, 1);
  } else {
    selectedCountries.value.push(code);
  }
}

// ── 上传提交 ───────────────────────────────────────────────────────────────────

/**
 * 提交上传：校验入参 → 调用 API → 显示结果页。
 *
 * @returns {Promise<void>}
 */
async function handleSubmit(): Promise<void> {
  if (!selectedFile.value) return;
  if (!useAutoSites.value && selectedCountries.value.length === 0) {
    errorMsg.value = "请至少选择一个投放国家";
    return;
  }

  uploading.value = true;
  errorMsg.value = "";
  try {
    const res = await uploadAdXlsx({
      file: selectedFile.value,
      adTypeFilter: adTypeFilter.value,
      countryFilter: useAutoSites.value ? [] : selectedCountries.value,
      dailyBudget: dailyBudget.value,
      defaultBid: defaultBid.value,
      closeMatchBid: closeMatchBid.value,
      looseMatchBid: looseMatchBid.value,
      substitutesBid: substitutesBid.value,
      complementsBid: complementsBid.value,
    });
    uploadResult.value = res;
    step.value = "result";
  } catch (err: unknown) {
    errorMsg.value = err instanceof Error ? err.message : "文件解析失败，请检查 Excel 格式";
  } finally {
    uploading.value = false;
  }
}

/**
 * 关闭弹窗并通知父组件打开队列抽屉。
 */
function handleViewQueue(): void {
  visible.value = false;
  emit("view-queue");
}

/**
 * 弹窗关闭后重置所有状态。
 */
function handleReset(): void {
  uploadRef.value?.clearFiles();
  selectedFile.value = null;
  uploading.value = false;
  errorMsg.value = "";
  step.value = "form";
  uploadResult.value = null;
  adTypeFilter.value = "all";
  useAutoSites.value = true;
  selectedCountries.value = [];
  dailyBudget.value = 1;
  defaultBid.value = 0.12;
  closeMatchBid.value = 0.12;
  looseMatchBid.value = 0.1;
  substitutesBid.value = 0.1;
  complementsBid.value = 0.1;
}
</script>

<style scoped lang="scss">
// ── 拖拽上传区 ─────────────────────────────────────────────────────────────────
.ad-upload-area {
  width: 100%;

  :deep(.el-upload-dragger) {
    width: 100%;
    padding: 28px 0;
    border-radius: 8px;
    transition:
      border-color 0.2s,
      background-color 0.2s;

    &:hover {
      background-color: var(--el-color-primary-light-9);
      border-color: var(--el-color-primary);
    }
  }
}

.ad-upload-icon {
  margin-bottom: 8px;
  font-size: 40px;
  color: var(--el-color-primary);
}

.ad-upload-text {
  font-size: 14px;
  color: #606266;

  b {
    color: #303133;
  }

  em {
    font-style: normal;
    color: var(--el-color-primary);
  }
}

.ad-upload-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

// ── 配置分区 ───────────────────────────────────────────────────────────────────
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 10px;

  &__title {
    display: flex;
    align-items: center;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }

  &__desc {
    font-size: 12px;
    line-height: 1.6;
    color: #909399;

    code {
      padding: 1px 5px;
      font-size: 12px;
      color: #e6a23c;
      background: #f0f2f5;
      border-radius: 3px;
    }
  }
}

.ad-type-group {
  :deep(.el-radio-button__inner) {
    padding: 7px 18px;
  }
}

// ── 国家选择 ───────────────────────────────────────────────────────────────────
.country-auto-tip {
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
  background: #f7f8fa;
  border-radius: 6px;
}

.country-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.country-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(66px, 1fr));
  gap: 8px;
}

.country-card {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: center;
  padding: 8px 4px;
  cursor: pointer;
  border: 1.5px solid #e4e7ed;
  border-radius: 8px;
  transition:
    border-color 0.15s,
    background-color 0.15s,
    box-shadow 0.15s;

  &:hover {
    background-color: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-5);
  }

  &.is-active {
    background-color: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--el-color-primary-light-5);
  }
}

.country-flag {
  font-size: 20px;
  line-height: 1;
}

.country-code {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}

.country-footer {
  font-size: 12px;
  line-height: 1.6;
}

.country-selected {
  font-weight: 500;
  color: var(--el-color-primary);
}

.country-muted {
  margin-left: 4px;
  color: #909399;
}

.country-empty {
  color: #f56c6c;
}

// ── 竞价设置 ───────────────────────────────────────────────────────────────────
.bidding-grid {
  display: grid;
  gap: 12px 16px;

  &--top {
    grid-template-columns: repeat(2, 1fr);
  }

  &--auto {
    grid-template-columns: repeat(4, 1fr);
  }
}

.bidding-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bidding-label {
  font-size: 12px;
  color: #606266;
}

.bidding-input {
  width: 100%;

  :deep(.el-input__wrapper) {
    padding-right: 32px;
  }
}

.bidding-sub-title {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 2px 0;
  font-size: 12px;
  font-weight: 600;
  color: #909399;

  &::before,
  &::after {
    flex: 1;
    height: 1px;
    content: "";
    background: #e4e7ed;
  }

  span {
    flex-shrink: 0;
    padding: 0 8px;
    white-space: nowrap;
  }
}

// ── 过渡动画 ───────────────────────────────────────────────────────────────────
.slide-down-enter-active,
.slide-down-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

// ── 解析结果 ───────────────────────────────────────────────────────────────────
.upload-result {
  &__summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 4px;
  }

  &__warnings {
    max-height: 180px;
    padding-left: 18px;
    margin: 0;
    overflow-y: auto;

    li {
      padding: 3px 0;
      font-size: 13px;
      line-height: 1.6;
      color: #e6a23c;
    }
  }
}
</style>
