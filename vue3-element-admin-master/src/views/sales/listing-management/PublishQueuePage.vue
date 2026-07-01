<template>
  <div class="tab-placeholder">
    <p class="tab-placeholder__text">刊登队列开发中…</p>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "ListingPublishQueuePage" });
</script>

<style scoped lang="scss">
.tab-placeholder {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 400px;

  &__text {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
  }
}
</style>
