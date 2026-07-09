<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      更多属性
    </div>
    <el-row :gutter="24">
      <!-- 左栏：站点内容 -->
      <el-col :span="12">
        <div class="draft-col__header">站点内容</div>
        <div class="draft-section__body">
          <el-button type="primary" size="small" style="margin-bottom: 16px">
            应用刊登模板
          </el-button>
          <p class="search-hint">搜索字段请在此处操作，不要用 Ctrl+F（可能会找不到）</p>
          <el-form label-position="left" label-width="200px" size="default">
            <el-form-item label="制造商" required>
              <el-input
                v-model="f.site.manufacturer"
                maxlength="100"
                show-word-limit
                placeholder="示例：Nike, Procter & Gamble"
                :class="{ 'lang-error': errors['site.manufacturer'] }"
                @input="onValidateSite('manufacturer', '制造商')"
              />
              <div v-if="errors['site.manufacturer']" class="lang-error-hint">
                {{ errors["site.manufacturer"] }}
              </div>
            </el-form-item>
            <el-form-item label="操作系统" required>
              <el-input
                v-model="f.site.operatingSystem"
                placeholder="示例：Linux, Mac OS X v10.4 Tiger"
                :class="{ 'lang-error': errors['site.operatingSystem'] }"
                @input="onValidateSite('operatingSystem', '操作系统')"
              />
              <div v-if="errors['site.operatingSystem']" class="lang-error-hint">
                {{ errors["site.operatingSystem"] }}
              </div>
            </el-form-item>
            <el-form-item label="价目表货币" required>
              <el-input v-model="f.site.listPriceCurrency" placeholder="示例：EUR" />
            </el-form-item>
            <el-form-item label="含税价目表" required>
              <el-input v-model="f.site.listPriceWithTax" placeholder="示例：69" />
            </el-form-item>
            <el-form-item label="原产国" required>
              <el-input
                v-model="f.site.countryOfOrigin"
                placeholder="示例：Großbritannien, Spanien"
                :class="{ 'lang-error': errors['site.countryOfOrigin'] }"
                @input="onValidateSite('countryOfOrigin', '原产国')"
              />
              <div v-if="errors['site.countryOfOrigin']" class="lang-error-hint">
                {{ errors["site.countryOfOrigin"] }}
              </div>
            </el-form-item>
            <el-form-item label="需要电池吗？" required>
              <el-select v-model="f.site.batteryRequired" class="draft-field-input--sm">
                <el-option label="是" value="yes" />
                <el-option label="否" value="no" />
              </el-select>
            </el-form-item>
            <el-form-item label="危险商品规管" required>
              <el-input
                v-model="f.site.hazardousGoods"
                placeholder="示例：GHS, Lagerung, Transport"
                :class="{ 'lang-error': errors['site.hazardousGoods'] }"
                @input="onValidateSite('hazardousGoods', '危险商品规管')"
              />
              <div v-if="errors['site.hazardousGoods']" class="lang-error-hint">
                {{ errors["site.hazardousGoods"] }}
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- 右栏：中文内容 -->
      <el-col :span="12">
        <div class="draft-col__header">中文内容</div>
        <div class="draft-section__body">
          <el-button type="primary" size="small" style="margin-bottom: 16px">
            应用刊登模板
          </el-button>
          <p class="search-hint">搜索字段请在此处操作，不要用 Ctrl+F（可能会找不到）</p>
          <el-form label-position="left" label-width="200px" size="default">
            <el-form-item label="制造商" required>
              <el-input
                v-model="f.cn.manufacturer"
                maxlength="100"
                show-word-limit
                placeholder="示例：耐克、宝洁"
                :class="{ 'lang-error': errors['cn.manufacturer'] }"
                @input="onValidateCn('manufacturer', '制造商')"
              />
              <div v-if="errors['cn.manufacturer']" class="lang-error-hint">
                {{ errors["cn.manufacturer"] }}
              </div>
            </el-form-item>
            <el-form-item label="操作系统" required>
              <el-input
                v-model="f.cn.operatingSystem"
                placeholder="示例：Linux、Mac OS X v10.4 Tiger"
                :class="{ 'lang-error': errors['cn.operatingSystem'] }"
                @input="onValidateCn('operatingSystem', '操作系统')"
              />
              <div v-if="errors['cn.operatingSystem']" class="lang-error-hint">
                {{ errors["cn.operatingSystem"] }}
              </div>
            </el-form-item>
            <el-form-item label="价目表货币" required>
              <el-input v-model="f.cn.listPriceCurrency" placeholder="示例：EUR" />
            </el-form-item>
            <el-form-item label="含税价目表" required>
              <el-input v-model="f.cn.listPriceWithTax" placeholder="示例：69" />
            </el-form-item>
            <el-form-item label="原产国" required>
              <el-input
                v-model="f.cn.countryOfOrigin"
                placeholder="示例：英国、西班牙"
                :class="{ 'lang-error': errors['cn.countryOfOrigin'] }"
                @input="onValidateCn('countryOfOrigin', '原产国')"
              />
              <div v-if="errors['cn.countryOfOrigin']" class="lang-error-hint">
                {{ errors["cn.countryOfOrigin"] }}
              </div>
            </el-form-item>
            <el-form-item label="需要电池吗？" required>
              <el-select v-model="f.cn.batteryRequired" class="draft-field-input--sm">
                <el-option label="是" value="yes" />
                <el-option label="否" value="no" />
              </el-select>
            </el-form-item>
            <el-form-item label="危险商品规管" required>
              <el-input
                v-model="f.cn.hazardousGoods"
                placeholder="示例：GHS、存储、运输"
                :class="{ 'lang-error': errors['cn.hazardousGoods'] }"
                @input="onValidateCn('hazardousGoods', '危险商品规管')"
              />
              <div v-if="errors['cn.hazardousGoods']" class="lang-error-hint">
                {{ errors["cn.hazardousGoods"] }}
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 更多属性 section：双栏布局（站点内容 / 中文内容）。
 * 制造商、操作系统、价目表、原产国、电池需求、危险品规管。
 * 实时校验语言：站点列校验站点语言，中文列校验中文。
 *
 * 通过 inject 获取父组件 provide 的 formData / currentSiteCode / langErrors。
 */
import { inject } from "vue";
import type { ComputedRef } from "vue";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";

defineOptions({ name: "MoreAttributesSection" });

const f = inject<any>("draftForm");
const siteCode = inject<ComputedRef<string>>("currentSiteCode")!;
const errors = inject<Record<string, string>>("langErrors")!;

/** 校验站点语言字段 */
function onValidateSite(field: string, label: string) {
  const key = `site.${field}`;
  const result = validateSiteLang(f.site[field], siteCode.value, label);
  errors[key] = result.message;
}

/** 校验中文字段 */
function onValidateCn(field: string, label: string) {
  const key = `cn.${field}`;
  const result = validateChinese(f.cn[field], label);
  errors[key] = result.message;
}
</script>

<style scoped lang="scss">
.search-hint {
  margin-bottom: 16px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
