<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      报价
    </div>
    <el-row :gutter="24">
      <!-- 左栏：站点内容 -->
      <el-col :span="12">
        <div class="draft-col__header">站点内容</div>
        <el-form
          label-position="left"
          label-width="200px"
          size="default"
          class="draft-section__body"
        >
          <el-form-item label="MSKU Seller SKU" required>
            <el-input
              v-model="f.site.msku"
              maxlength="40"
              show-word-limit
              placeholder="仅字母、数字、小数点、短横线"
            />
          </el-form-item>
          <el-form-item label="商品编码" required>
            <el-input v-model="f.site.externalProductId" placeholder="示例：714532191586" />
          </el-form-item>
          <el-form-item label="商品状况" required>
            <el-select v-model="f.site.productCondition" class="draft-field-input--md">
              <el-option label="Neu" value="Neu" />
              <el-option label="Gebraucht" value="Gebraucht" />
            </el-select>
          </el-form-item>
          <el-form-item label="价格" required>
            <div class="draft-field-row">
              <el-input v-model="f.site.price" placeholder="50.00" class="draft-field-input--md" />
              <span class="draft-field-unit">{{ f.site.currency }}</span>
            </div>
          </el-form-item>
          <el-form-item label="优惠价">
            <div class="draft-field-row">
              <el-input
                v-model="f.site.promotionPrice"
                placeholder="219.99"
                class="draft-field-input--md"
              />
              <span class="draft-field-unit">{{ f.site.currency }}</span>
            </div>
          </el-form-item>
          <el-form-item label="优惠开始日期">
            <el-date-picker
              v-model="f.site.promotionStartDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="2017-06-30"
              class="draft-field-input--md"
            />
          </el-form-item>
          <el-form-item label="优惠结束日期">
            <el-date-picker
              v-model="f.site.promotionEndDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="2017-07-01"
              class="draft-field-input--md"
            />
          </el-form-item>
        </el-form>
      </el-col>

      <!-- 右栏：中文内容 -->
      <el-col :span="12">
        <div class="draft-col__header">中文内容</div>
        <el-form
          label-position="left"
          label-width="200px"
          size="default"
          class="draft-section__body"
        >
          <el-form-item label="MSKU" required>
            <el-input
              v-model="f.cn.msku"
              maxlength="40"
              show-word-limit
              placeholder="仅字母、数字、小数点、短横线"
            />
          </el-form-item>
          <el-form-item label="商品编码" required>
            <el-input v-model="f.cn.externalProductId" placeholder="示例：714532191586" />
          </el-form-item>
          <el-form-item label="商品状况" required>
            <el-select v-model="f.cn.productCondition" class="draft-field-input--md">
              <el-option label="全新" value="Neu" />
              <el-option label="二手" value="Gebraucht" />
            </el-select>
          </el-form-item>
          <el-form-item label="价格" required>
            <div class="draft-field-row">
              <el-input v-model="f.cn.price" placeholder="50.00" class="draft-field-input--md" />
              <span class="draft-field-unit">{{ f.cn.currency }}</span>
            </div>
          </el-form-item>
          <el-form-item label="优惠价">
            <div class="draft-field-row">
              <el-input
                v-model="f.cn.promotionPrice"
                placeholder="219.99"
                class="draft-field-input--md"
              />
              <span class="draft-field-unit">{{ f.cn.currency }}</span>
            </div>
          </el-form-item>
          <el-form-item label="优惠开始日期">
            <el-date-picker
              v-model="f.cn.promotionStartDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="2017-06-30"
              class="draft-field-input--md"
            />
          </el-form-item>
          <el-form-item label="优惠结束日期">
            <el-date-picker
              v-model="f.cn.promotionEndDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="2017-07-01"
              class="draft-field-input--md"
            />
          </el-form-item>
        </el-form>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 报价 section：双栏布局（站点内容 / 中文内容）。
 * MSKU、商品编码、商品状况、价格、优惠价、优惠日期。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 */
import { inject } from "vue";

defineOptions({ name: "PricingSection" });

const f = inject<any>("draftForm");
</script>
