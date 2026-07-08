<template>
  <el-dialog
    v-model="isVisible"
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
          <el-button :icon="ZoomIn" circle size="small" @click="handleZoomIn" />
          <el-button :icon="ZoomOut" circle size="small" @click="handleZoomOut" />
          <el-button :icon="RefreshRight" circle size="small" @click="handleRotate" />
          <el-button :icon="RefreshLeft" circle size="small" @click="handleRotateBack" />
        </div>
        <div class="confirm-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="isConfirming" @click="handleConfirm">确认</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 头像裁剪弹窗组件。
 * 基于 cropperjs v2 实现 1:1 裁剪，确认后以 Blob 形式 emit 给父组件。
 */
import type Cropper from "cropperjs";
import { nextTick, ref, watch } from "vue";
import { RefreshLeft, RefreshRight, ZoomIn, ZoomOut } from "@element-plus/icons-vue";
import CropperJS from "cropperjs";

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "confirm", payload: { blob: Blob; dataUrl: string }): void;
  (e: "cancel"): void;
}>();

const props = defineProps<{
  modelValue: boolean;
  srcUrl: string;
}>();

const isVisible = ref(props.modelValue);
const imgRef = ref<HTMLImageElement | null>(null);
const isConfirming = ref(false);
let cropperInstance: Cropper | null = null;

watch(
  () => props.modelValue,
  (val) => {
    isVisible.value = val;
    if (val) nextTick(() => initCropper());
  }
);

watch(isVisible, (val) => {
  if (!val) emit("update:modelValue", false);
});

/** 初始化 Cropper.js v2 实例。 */
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
  nextTick(() => {
    const sel = cropperInstance?.getCropperSelection();
    if (sel) sel.aspectRatio = 1;
  });
}

/** 销毁 Cropper.js 实例，释放内存。 */
function destroyCropper(): void {
  if (cropperInstance) {
    cropperInstance.destroy();
    cropperInstance = null;
  }
}

/** 弹窗彻底关闭后的清理（destroy-on-close 配合）。 */
function handleDialogClosed(): void {
  destroyCropper();
}

/** 用户确认裁剪：导出选区图像。 */
async function handleConfirm(): Promise<void> {
  if (!cropperInstance) return;
  isConfirming.value = true;
  try {
    const canvas = await cropperInstance
      .getCropperSelection()
      ?.$toCanvas({ width: 512, height: 512 });
    if (!canvas) throw new Error("裁剪区域无效");
    await new Promise<void>((resolve, reject) => {
      canvas.toBlob(
        (blob: Blob | null) => {
          if (!blob) {
            reject(new Error("导出 Blob 失败"));
            return;
          }
          emit("confirm", { blob, dataUrl: canvas.toDataURL("image/jpeg", 0.85) });
          isVisible.value = false;
          resolve();
        },
        "image/jpeg",
        0.85
      );
    });
  } finally {
    isConfirming.value = false;
  }
}

/** 取消裁剪。 */
function handleCancel(): void {
  isVisible.value = false;
  emit("cancel");
}

/** 放大。 */
function handleZoomIn(): void {
  cropperInstance?.getCropperImage()?.$zoom(0.1);
}

/** 缩小。 */
function handleZoomOut(): void {
  cropperInstance?.getCropperImage()?.$zoom(-0.1);
}

/** 顺时针旋转 90 度。 */
function handleRotate(): void {
  cropperInstance?.getCropperImage()?.$rotate("90deg");
}

/** 逆时针旋转 90 度。 */
function handleRotateBack(): void {
  cropperInstance?.getCropperImage()?.$rotate("-90deg");
}
</script>

<style scoped lang="scss">
.cropper-wrapper {
  height: 400px;
  overflow: hidden;
  background: var(--el-fill-color);
  border-radius: 6px;

  .cropper-source {
    display: block;
    max-width: 100%;
  }

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
