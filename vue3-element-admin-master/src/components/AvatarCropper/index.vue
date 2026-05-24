<template>
  <el-dialog
    v-model="visible"
    title="裁剪头像"
    :width="520"
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
          <el-button :icon="RefreshRight" circle size="small" title="顺时针旋转" @click="handleRotate" />
          <el-button :icon="RefreshLeft" circle size="small" title="逆时针旋转" @click="handleRotateBack" />
        </div>
        <div class="confirm-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="confirming" @click="handleConfirm">确认裁剪</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 头像裁剪弹窗组件。
 * 基于 cropperjs 实现 1:1 圆形预览裁剪，确认后以 Blob 形式 emit 给父组件。
 * 所属板块：通用组件。
 */
import type Cropper from 'cropperjs'

import { nextTick, ref, watch } from 'vue'
import { RefreshLeft, RefreshRight, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import CropperJS from 'cropperjs'

import 'cropperjs/dist/cropper.css'

const emit = defineEmits<{
  /** v-model 更新 */
  (e: 'update:modelValue', value: boolean): void
  /** 用户确认裁剪，携带 Blob 和预览 dataUrl */
  (e: 'confirm', payload: { blob: Blob; dataUrl: string }): void
  /** 用户取消 */
  (e: 'cancel'): void
}>()

const props = defineProps<{
  modelValue: boolean
  srcUrl: string
}>()
const visible = ref(props.modelValue)
const imgRef = ref<HTMLImageElement | null>(null)
const confirming = ref(false)
let cropperInstance: Cropper | null = null

// 同步外部 v-model → 内部 visible
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      nextTick(() => initCropper())
    }
  },
)

// 同步内部关闭 → 外部 v-model
watch(visible, (val) => {
  if (!val) emit('update:modelValue', false)
})

/**
 * 初始化 Cropper.js 实例，固定 1:1 纵横比并显示圆形预览。
 */
function initCropper(): void {
  if (!imgRef.value) return
  destroyCropper()
  cropperInstance = new CropperJS(imgRef.value, {
    aspectRatio: 1,
    viewMode: 1,
    dragMode: 'move',
    autoCropArea: 0.85,
    restore: false,
    guides: false,
    highlight: false,
    cropBoxMovable: false,
    cropBoxResizable: false,
    toggleDragModeOnDblclick: false,
    preview: [],
  })
}

/**
 * 销毁 Cropper.js 实例，释放内存。
 */
function destroyCropper(): void {
  if (cropperInstance) {
    cropperInstance.destroy()
    cropperInstance = null
  }
}

/**
 * 弹窗彻底关闭后的清理（destroy-on-close 配合）。
 */
function handleDialogClosed(): void {
  destroyCropper()
}

/**
 * 用户确认裁剪：导出 canvas 转为 Blob，emit 给父组件。
 */
async function handleConfirm(): Promise<void> {
  if (!cropperInstance) return
  confirming.value = true
  try {
    const canvas = cropperInstance.getCroppedCanvas({ width: 512, height: 512 })
    await new Promise<void>((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error('导出 Blob 失败'))
            return
          }
          const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
          emit('confirm', { blob, dataUrl })
          visible.value = false
          resolve()
        },
        'image/jpeg',
        0.85,
      )
    })
  } finally {
    confirming.value = false
  }
}

function handleCancel(): void {
  visible.value = false
  emit('cancel')
}

function handleZoomIn(): void {
  cropperInstance?.zoom(0.1)
}

function handleZoomOut(): void {
  cropperInstance?.zoom(-0.1)
}

function handleRotate(): void {
  cropperInstance?.rotate(90)
}

function handleRotateBack(): void {
  cropperInstance?.rotate(-90)
}
</script>

<style scoped lang="scss">
.cropper-wrapper {
  display: flex;
  justify-content: center;
  max-height: 380px;
  overflow: hidden;

  .cropper-source {
    display: block;
    max-width: 100%;
  }
}

.cropper-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .zoom-actions {
    display: flex;
    gap: 8px;
  }

  .confirm-actions {
    display: flex;
    gap: 8px;
  }
}
</style>
