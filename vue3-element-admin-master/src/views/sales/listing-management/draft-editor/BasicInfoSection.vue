<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      基本信息
    </div>
    <el-form label-position="left" label-width="200px" size="default" class="draft-section__form">
      <el-form-item label="店铺" required>
        <el-select v-model="f.shop" placeholder="请选择" style="width: 280px" />
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
        <div class="field-hint">首字母大写</div>
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
        <div class="field-row">
          <el-input v-model="f.packageLength" placeholder="示例：75.50" style="width: 100px" />
          <el-input v-model="f.packageWidth" placeholder="示例：10.00" style="width: 100px" />
          <el-input v-model="f.packageHeight" placeholder="示例：50.00" style="width: 100px" />
          <el-select v-model="f.packageDimensionUnit" style="width: 120px">
            <el-option label="Zentimeter" value="Zentimeter" />
            <el-option label="Inch" value="Inch" />
          </el-select>
        </div>
      </el-form-item>

      <el-form-item label="包裹重量 Paketgewicht" required>
        <div class="field-row">
          <el-input v-model="f.packageWeight" placeholder="示例：24" style="width: 140px" />
          <el-select v-model="f.packageWeightUnit" style="width: 100px">
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
import { inject } from "vue";

defineOptions({ name: "BasicInfoSection" });

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

.field-hint {
  margin-top: 4px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
