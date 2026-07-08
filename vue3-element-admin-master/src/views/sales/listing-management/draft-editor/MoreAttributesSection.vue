<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      更多属性
    </div>
    <div class="draft-section__body">
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
          <el-select v-model="f.batteryRequired" class="draft-field-input--sm">
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
/**
 * 更多属性 section：制造商、操作系统、价目表、原产国、电池需求、危险品规管。
 *
 * 通过 inject 获取父组件 provide 的 formData。
 */
import { inject } from "vue";

defineOptions({ name: "MoreAttributesSection" });

/** 注入父组件共享的草稿表单数据 */
const f = inject<any>("draftForm");
</script>

<style scoped lang="scss">
.search-hint {
  margin-bottom: 16px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
