<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      报价
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__form">
      <el-form-item label="MSKU Seller SKU" required>
        <el-input
          v-model="f.msku"
          maxlength="40"
          show-word-limit
          placeholder="仅字母、数字、小数点、短横线、下划线、空格、加减号"
        />
      </el-form-item>

      <el-form-item label="商品编码 Externe Produkt-ID" required>
        <el-input v-model="f.externalProductId" placeholder="示例：714532191586" />
      </el-form-item>

      <el-form-item label="商品状况 Artikelzustand" required>
        <el-select v-model="f.productCondition" style="width: 200px">
          <el-option label="Neu" value="Neu" />
          <el-option label="Gebraucht" value="Gebraucht" />
        </el-select>
      </el-form-item>

      <el-form-item label="价格 Ihr Preis" required>
        <div class="field-row">
          <el-input v-model="f.price" placeholder="示例：50.00" style="width: 160px" />
          <span class="field-unit">{{ f.currency }}</span>
        </div>
      </el-form-item>

      <el-form-item label="优惠价 Angebotspreis">
        <div class="field-row">
          <el-input v-model="f.promotionPrice" placeholder="示例：219.99" style="width: 160px" />
          <span class="field-unit">{{ f.currency }}</span>
        </div>
      </el-form-item>

      <el-form-item label="优惠开始日期 Startdatum für den Angebotspreis">
        <el-date-picker
          v-model="f.promotionStartDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="示例：2017-06-30"
          style="width: 200px"
        />
      </el-form-item>

      <el-form-item label="优惠结束日期 Enddatum für den Angebotspreis">
        <el-date-picker
          v-model="f.promotionEndDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="示例：2017-07-01"
          style="width: 200px"
        />
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
import { inject } from "vue";

defineOptions({ name: "PricingSection" });

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

.field-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.field-unit {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
