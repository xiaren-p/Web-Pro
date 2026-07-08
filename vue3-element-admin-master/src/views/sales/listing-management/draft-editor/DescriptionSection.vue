<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      描述
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__form">
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
import { inject } from "vue";

defineOptions({ name: "DescriptionSection" });

const f = inject<any>("draftForm");
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
</style>
