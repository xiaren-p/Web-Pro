<template>
  <el-dialog
    v-model="visible"
    title="裁剪头像"
    :width="580"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="handleDialogClosed"
  >
    <div class="cropper-wrapper">
      <img ref="imgRef" class="cropper-source" :src="srcUrl" alt="待裁剪图片" />
    </div>

    <template #footer>
      <div class="cropper-footer">
        <div class="zoom-actions">
          <el-button :icon="ZoomIn" circle size="small" title="放大" @click="handleZoomIn" />
          <el-button :icon="ZoomOut" circle size="small" title="缩小" @click="handleZoomOut" />
          <el-button
            :icon="RefreshRight"
            circle
            size="small"
            title="顺时针旋转"
            @click="handleRotate"
          />
          <el-button
            :icon="RefreshLeft"
            circle
            size="small"
            title="逆时针旋转"
            @click="handleRotateBack"
          />
        </div>
        <div class="confirm-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="confirming" @click="handleConfirm">
            确认裁剪
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 头像裁剪弹窗组件。
 * 基于 cropperjs v2 实现 1:1 裁剪，确认后以 Blob 形式 emit 给父组件。
 * 所属板块：通用组件。
 */
import type Cropper from "cropperjs";

import { nextTick, ref, watch } from "vue";
import { RefreshLeft, RefreshRight, ZoomIn, ZoomOut } from "@element-plus/icons-vue";
import CropperJS from "cropperjs";

const emit = defineEmits<{
  /** v-model 更新 */
  (e: "update:modelValue", value: boolean): void;
  /** 用户确认裁剪，携带 Blob 和预览 dataUrl */
  (e: "confirm", payload: { blob: Blob; dataUrl: string }): void;
  /** 用户取消 */
  (e: "cancel"): void;
}>();

const props = defineProps<{
  modelValue: boolean;
  srcUrl: string;
}>();
const visible = ref(props.modelValue);
const imgRef = ref<HTMLImageElement | null>(null);
const confirming = ref(false);
let cropperInstance: Cropper | null = null;

// 同步外部 v-model → 内部 visible
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val) {
      nextTick(() => initCropper());
    }
  }
);

// 同步内部关闭 → 外部 v-model
watch(visible, (val) => {
  if (!val) emit("update:modelValue", false);
});

/**
 * 初始化 Cropper.js v2 实例。
 * v2 不再支持 v1 的 options（viewMode/dragMode/aspectRatio 等已移除），
 * 改用 template 字符串声明 web components 布局，
 * 并在初始化后直接设置 selection.aspectRatio。
 */
function initCropper(): void {
  if (!imgRef.value) return;
  destroyCropper();
  cropperInstance = new CropperJS(imgRef.value, {
    template: `<cropper-canvas background>
      <cropper-image></cropper-image>
      <cropper-shade></cropper-shade>
      <cropper-selection initial-coverage="0.85" movable resizable>
        <cropper-grid bordered covered></cropper-grid>
        <cropper-crosshair></cropper-crosshair>
        <cropper-handle action="move"></cropper-handle>
        <cropper-handle action="n-resize"></cropper-handle>
        <cropper-handle action="e-resize"></cropper-handle>
        <cropper-handle action="s-resize"></cropper-handle>
        <cropper-handle action="w-resize"></cropper-handle>
        <cropper-handle action="ne-resize"></cropper-handle>
        <cropper-handle action="nw-resize"></cropper-handle>
        <cropper-handle action="se-resize"></cropper-handle>
        <cropper-handle action="sw-resize"></cropper-handle>
      </cropper-selection>
    </cropper-canvas>`,
  });
  // v2 中 aspectRatio 是 selection 元素的属性，必须在初始化完成后设置
  nextTick(() => {
    const sel = cropperInstance?.getCropperSelection();
    if (sel) sel.aspectRatio = 1;
  });
}

/**
 * 销毁 Cropper.js 实例，释放内存。
 */
function destroyCropper(): void {
  if (cropperInstance) {
    cropperInstance.destroy();
    cropperInstance = null;
  }
}

/**
 * 弹窗彻底关闭后的清理（destroy-on-close 配合）。
 */
function handleDialogClosed(): void {
  destroyCropper();
}

/**
 * 用户确认裁剪：用 getCropperSelection().$toCanvas() 导出选区图像。
 * getCropperSelection 是 v2 专用 API，仅输出选中区域内容。
 */
async function handleConfirm(): Promise<void> {
  if (!cropperInstance) return;
  confirming.value = true;
  try {
    const canvas = await cropperInstance.getCropperSelection()?.$toCanvas({
      width: 512,
      height: 512,
    });
    if (!canvas) throw new Error("裁剪区域无效，请确认已选择图片");
    await new Promise<void>((resolve, reject) => {
      canvas.toBlob(
        (blob: Blob | null) => {
          if (!blob) {
            reject(new Error("导出 Blob 失败"));
            return;
          }
          const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
          emit("confirm", { blob, dataUrl });
          visible.value = false;
          resolve();
        },
        "image/jpeg",
        0.85
      );
    });
  } finally {
    confirming.value = false;
  }
}

function handleCancel(): void {
  visible.value = false;
  emit("cancel");
}

function handleZoomIn(): void {
  cropperInstance?.getCropperImage()?.$zoom(0.1);
}

function handleZoomOut(): void {
  cropperInstance?.getCropperImage()?.$zoom(-0.1);
}

function handleRotate(): void {
  cropperInstance?.getCropperImage()?.$rotate("90deg");
}

function handleRotateBack(): void {
  cropperInstance?.getCropperImage()?.$rotate("-90deg");
}
</script>

<style scoped lang="scss">
.cropper-wrapper {
  height: 400px;
  overflow: hidden;
  background: #161616;
  border-radius: 6px;

  // 原始 img 节点：Cropper.js v2 初始化后会隐藏它，此样式仅在初始化前短暂生效
  .cropper-source {
    display: block;
    max-width: 100%;
  }

  // Cropper.js v2 以 Web Component 形式渲染，<cropper-canvas> 不会自动撑满父容器，
  // 必须显式设置 width/height 才能填满 400px 包裹层，否则画布仅与图片原始尺寸等高，
  // 剩余空间显示背景色（黑色），造成截图中所示的"只有顶部有图、下方全黑"的错误效果。
  :deep(cropper-canvas) {
    display: block;
    width: 100%;
    height: 100%;
  }
}

.cropper-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;

  .zoom-actions {
    display: flex;
    gap: 6px;
  }

  .confirm-actions {
    display: flex;
    gap: 8px;
  }
}
</style>
