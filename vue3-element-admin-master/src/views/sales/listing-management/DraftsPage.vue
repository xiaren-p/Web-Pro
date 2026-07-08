<template>
  <div class="drafts-page">
    <section class="drafts-page__filters content-block">
      <DraftFilterBar />
    </section>

    <section class="drafts-page__table content-block content-block--flush">
      <DraftActionBar @add-draft="handleAddDraft" />
      <DraftTable />
      <DraftPagination />
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import DraftFilterBar from "./components/DraftFilterBar.vue";
import DraftActionBar from "./components/DraftActionBar.vue";
import DraftTable from "./components/DraftTable.vue";
import DraftPagination from "./components/DraftPagination.vue";

defineOptions({ name: "ListingDraftsPage" });

const router = useRouter();

function handleAddDraft() {
  router.push("/sales/listing-management/draft-editor");
}
</script>

<style scoped lang="scss">
.drafts-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: var(--spacing-6);

  &__filters {
    padding-bottom: 12px;
  }

  &__table {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 420px;
  }
}
</style>
