<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      描述
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__body">
      <el-form-item label="产品描述 Produktbeschreibung" required>
        <el-input
          v-model="f.productDescription"
          type="textarea"
          :rows="6"
          maxlength="2000"
          show-word-limit
        />
      </el-form-item>

      <el-form-item
        v-for="(_, idx) in f.bulletPoints"
        :key="idx"
        :label="idx === 0 ? '要点 Aufzählungspunkt' : ''"
        required
      >
        <el-input
          v-model="f.bulletPoints[idx]"
          maxlength="700"
          show-word-limit
          placeholder="示例：Blumenmuster mit Blumenformen"
        />
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
/**
 * 描述 section：产品描述 textarea（2000字上限）+ 5 条要点（各 700 字上限）。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 */
import { inject } from "vue";

defineOptions({ name: "DescriptionSection" });

/** 注入父组件共享的草稿表单数据 */
const f = inject<any>("draftForm");
</script>
