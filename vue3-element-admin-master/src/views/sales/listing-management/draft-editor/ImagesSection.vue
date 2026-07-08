<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      图片
    </div>
    <div class="draft-section__body">
      <el-upload drag multiple :auto-upload="false" :on-change="handleChange" accept="image/*">
        <el-icon :size="40"><UploadFilled /></el-icon>
        <div class="upload-hint">将图片拖拽到此处即可上传</div>
      </el-upload>
      <div class="upload-tip">图片建议：使用纯白背景，商品占比 85% 以上</div>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 图片 section：拖拽上传区域。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 * 上传文件追加到 formData.images 数组。
 */
import { inject } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";

defineOptions({ name: "ImagesSection" });

/** 注入父组件共享的草稿表单数据 */
const f = inject<any>("draftForm");

/** 文件变更回调：将原始文件追加到 images 数组 */
function handleChange(file: UploadFile) {
  if (file.raw) f.images.push(file.raw);
}
</script>

<style scoped lang="scss">
.upload-hint {
  margin-top: 8px;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.upload-tip {
  margin-top: 12px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
