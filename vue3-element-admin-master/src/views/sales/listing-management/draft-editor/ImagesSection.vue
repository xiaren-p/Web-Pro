<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      图片
    </div>
    <div class="draft-section__form">
      <el-upload drag multiple :auto-upload="false" :on-change="handleChange" accept="image/*">
        <el-icon :size="40"><UploadFilled /></el-icon>
        <div class="upload-hint">将图片拖拽到此处即可上传</div>
      </el-upload>
      <div class="upload-tip">图片建议：使用纯白背景，商品占比 85% 以上</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { inject } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";

defineOptions({ name: "ImagesSection" });

const f = inject<any>("draftForm");

function handleChange(file: UploadFile) {
  if (file.raw) f.images.push(file.raw);
}
</script>

<style scoped lang="scss">
.draft-section {
  &__header {
    display: flex;
    gap: 8px;
    align-items: center;
    padding-bottom: 16px;
    margin-bottom: 20px;
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-subtle);
  }

  &__bar {
    display: inline-block;
    width: 4px;
    height: 18px;
    background: var(--color-primary-600);
    border-radius: 2px;
  }

  &__form {
    padding: 20px 24px;
    background: var(--surface-base);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
  }
}

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
