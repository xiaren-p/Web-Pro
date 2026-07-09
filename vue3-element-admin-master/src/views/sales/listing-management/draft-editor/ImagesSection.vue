<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      图片
    </div>
    <el-row :gutter="24">
      <!-- 左栏：站点图片 -->
      <el-col :span="12">
        <div class="draft-col__header">站点图片</div>
        <div class="draft-section__body">
          <el-upload
            drag
            multiple
            :auto-upload="false"
            :on-change="handleSiteChange"
            accept="image/*"
          >
            <el-icon :size="40"><UploadFilled /></el-icon>
            <div class="upload-hint">将站点图片拖拽到此处</div>
          </el-upload>
          <div class="upload-tip">图片建议：使用纯白背景，商品占比 85% 以上</div>
        </div>
      </el-col>

      <!-- 右栏：中文图片 -->
      <el-col :span="12">
        <div class="draft-col__header">中文图片</div>
        <div class="draft-section__body">
          <el-upload
            drag
            multiple
            :auto-upload="false"
            :on-change="handleCnChange"
            accept="image/*"
          >
            <el-icon :size="40"><UploadFilled /></el-icon>
            <div class="upload-hint">将中文图片拖拽到此处</div>
          </el-upload>
          <div class="upload-tip">图片建议：使用纯白背景，商品占比 85% 以上</div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 图片 section：双栏布局（站点图片 / 中文图片）。
 * 上传文件分别追加到 formData.siteImages / formData.cnImages。
 */
import { inject } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";

defineOptions({ name: "ImagesSection" });

const f = inject<any>("draftForm");

/** 站点图片变更回调 */
function handleSiteChange(file: UploadFile) {
  if (file.raw) {
    if (!f.siteImages) f.siteImages = [];
    f.siteImages.push(file.raw);
  }
}

/** 中文图片变更回调 */
function handleCnChange(file: UploadFile) {
  if (file.raw) {
    if (!f.cnImages) f.cnImages = [];
    f.cnImages.push(file.raw);
  }
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
