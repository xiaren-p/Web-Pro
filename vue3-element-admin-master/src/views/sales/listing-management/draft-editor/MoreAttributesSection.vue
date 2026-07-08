<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      更多属性
    </div>
    <div class="draft-section__form">
      <el-button type="primary" size="small" style="margin-bottom: 16px">应用刊登模板</el-button>
      <p class="search-hint">搜索字段请在此处操作，不要用 Ctrl+F（可能会找不到）</p>

      <el-form label-position="left" label-width="200px" size="default">
        <el-form-item label="制造商 Hersteller" required>
          <el-input
            v-model="f.manufacturer"
            maxlength="100"
            show-word-limit
            placeholder="示例：Nike, Procter & Gamble"
          />
        </el-form-item>

        <el-form-item label="操作系统 Betriebssystem" required>
          <el-input v-model="f.operatingSystem" placeholder="示例：Linux, Mac OS X v10.4 Tiger" />
        </el-form-item>

        <el-form-item label="价目表货币 Listenpreis – Währung" required>
          <el-input v-model="f.listPriceCurrency" placeholder="示例：EUR" />
        </el-form-item>

        <el-form-item label="含税价目表 Listenpreis mit Steuern" required>
          <el-input v-model="f.listPriceWithTax" placeholder="示例：69" />
        </el-form-item>

        <el-form-item label="原产国 Ursprungsland" required>
          <el-input v-model="f.countryOfOrigin" placeholder="示例：Großbritannien, Spanien" />
        </el-form-item>

        <el-form-item label="需要电池吗？Sind Batterien erforderlich?" required>
          <el-select v-model="f.batteryRequired" style="width: 160px">
            <el-option label="是" value="yes" />
            <el-option label="否" value="no" />
          </el-select>
        </el-form-item>

        <el-form-item label="危险商品规管 Gefahrgutvorschriften" required>
          <el-input v-model="f.hazardousGoods" placeholder="示例：GHS, Lagerung, Transport" />
        </el-form-item>
      </el-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { inject } from "vue";

defineOptions({ name: "MoreAttributesSection" });

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

.search-hint {
  margin-bottom: 16px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
