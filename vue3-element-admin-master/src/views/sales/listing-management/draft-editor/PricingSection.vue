<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      报价
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__body">
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
        <el-select v-model="f.productCondition" class="draft-field-input--md">
          <el-option label="Neu" value="Neu" />
          <el-option label="Gebraucht" value="Gebraucht" />
        </el-select>
      </el-form-item>

      <el-form-item label="价格 Ihr Preis" required>
        <div class="draft-field-row">
          <el-input v-model="f.price" placeholder="示例：50.00" class="draft-field-input--md" />
          <span class="draft-field-unit">{{ f.currency }}</span>
        </div>
      </el-form-item>

      <el-form-item label="优惠价 Angebotspreis">
        <div class="draft-field-row">
          <el-input
            v-model="f.promotionPrice"
            placeholder="示例：219.99"
            class="draft-field-input--md"
          />
          <span class="draft-field-unit">{{ f.currency }}</span>
        </div>
      </el-form-item>

      <el-form-item label="优惠开始日期 Startdatum für den Angebotspreis">
        <el-date-picker
          v-model="f.promotionStartDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="示例：2017-06-30"
          class="draft-field-input--md"
        />
      </el-form-item>

      <el-form-item label="优惠结束日期 Enddatum für den Angebotspreis">
        <el-date-picker
          v-model="f.promotionEndDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="示例：2017-07-01"
          class="draft-field-input--md"
        />
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
/**
 * 报价 section：MSKU、商品编码、商品状况、价格、优惠价、优惠日期。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 */
import { inject } from "vue";

defineOptions({ name: "PricingSection" });

/** 注入父组件共享的草稿表单数据 */
const f = inject<any>("draftForm");
</script>
