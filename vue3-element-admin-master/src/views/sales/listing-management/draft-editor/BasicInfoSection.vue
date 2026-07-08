<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      基本信息
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__body">
      <el-form-item label="店铺" required>
        <el-select v-model="f.shop" placeholder="请选择" class="draft-field-input--lg" />
      </el-form-item>

      <el-form-item label="上架类型" required>
        <el-radio-group v-model="f.listingType">
          <el-radio value="new">创建新品</el-radio>
          <el-radio value="append">追加变体</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="Amazon分类" required>
        <el-input v-model="f.amazonCategory" placeholder="例：Software > Kinder & Familie" />
      </el-form-item>

      <el-form-item label="商品类型 Product Type" required>
        <el-input v-model="f.productType" placeholder="例：PHYSICAL_SOFTWARE" />
      </el-form-item>

      <el-form-item label="商品名称 Artikelname" required>
        <el-input
          v-model="f.productName"
          type="textarea"
          :rows="2"
          maxlength="200"
          show-word-limit
          placeholder="示例：Blaue Adidas-Turnschuhe"
        />
        <div class="draft-field-hint">首字母大写</div>
      </el-form-item>

      <el-form-item label="商品亮点 Artikel-Highlight">
        <el-input
          v-model="f.productHighlights"
          maxlength="125"
          show-word-limit
          placeholder="示例：Atmungsaktives Material"
        />
      </el-form-item>

      <el-form-item label="品牌名 Markenname" required>
        <el-input v-model="f.brandName" maxlength="100" show-word-limit placeholder="示例：Sony" />
      </el-form-item>

      <el-form-item label="包装尺寸 Paket-Abmessungen" required>
        <div class="draft-field-row">
          <el-input v-model="f.packageLength" placeholder="75.50" class="draft-field-input--sm" />
          <el-input v-model="f.packageWidth" placeholder="10.00" class="draft-field-input--sm" />
          <el-input v-model="f.packageHeight" placeholder="50.00" class="draft-field-input--sm" />
          <el-select v-model="f.packageDimensionUnit" class="draft-field-input--md">
            <el-option label="Zentimeter" value="Zentimeter" />
            <el-option label="Inch" value="Inch" />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item label="包裹重量 Paketgewicht" required>
        <div class="draft-field-row">
          <el-input v-model="f.packageWeight" placeholder="24" class="draft-field-input--sm" />
          <el-select v-model="f.packageWeightUnit" class="draft-field-input--sm">
            <el-option label="Pfund" value="Pfund" />
            <el-option label="Kilogramm" value="Kilogramm" />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item label="销售类型" required>
        <el-radio-group v-model="f.salesType">
          <el-radio value="single">单体</el-radio>
          <el-radio value="variant">变体</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="配送渠道" required>
        <el-radio-group v-model="f.deliveryChannel">
          <el-radio value="FBA">FBA</el-radio>
          <el-radio value="FBM">FBM</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
/**
 * 基本信息 section：店铺、上架类型、Amazon分类、商品类型、商品名称、
 * 商品亮点、品牌名、包装尺寸、包裹重量、销售类型、配送渠道。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 */
import { inject } from "vue";

defineOptions({ name: "BasicInfoSection" });

/** 注入父组件共享的草稿表单数据 */
const f = inject<any>("draftForm");
</script>
