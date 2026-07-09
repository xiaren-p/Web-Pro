<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      基本信息
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
          <el-form-item label="店铺" required>
            <el-select v-model="f.site.shop" placeholder="请选择" class="draft-field-input--lg" />
          </el-form-item>
          <el-form-item label="上架类型" required>
            <el-radio-group v-model="f.site.listingType">
              <el-radio value="new">创建新品</el-radio>
              <el-radio value="append">追加变体</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="Amazon分类" required>
            <el-input
              v-model="f.site.amazonCategory"
              placeholder="例：Software > Kinder & Familie"
            />
          </el-form-item>
          <el-form-item label="商品类型 Product Type" required>
            <el-input v-model="f.site.productType" placeholder="例：PHYSICAL_SOFTWARE" />
          </el-form-item>
          <el-form-item label="商品名称" required>
            <el-input
              v-model="f.site.productName"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              placeholder="示例：Blaue Adidas-Turnschuhe"
              :class="{ 'lang-error': errors['site.productName'] }"
              @input="onValidateSite('productName', '商品名称')"
            />
            <div v-if="errors['site.productName']" class="lang-error-hint">
              {{ errors["site.productName"] }}
            </div>
            <div class="draft-field-hint">首字母大写</div>
          </el-form-item>
          <el-form-item label="商品亮点">
            <el-input
              v-model="f.site.productHighlights"
              maxlength="125"
              show-word-limit
              placeholder="示例：Atmungsaktives Material"
              :class="{ 'lang-error': errors['site.productHighlights'] }"
              @input="onValidateSite('productHighlights', '商品亮点')"
            />
            <div v-if="errors['site.productHighlights']" class="lang-error-hint">
              {{ errors["site.productHighlights"] }}
            </div>
          </el-form-item>
          <el-form-item label="品牌名" required>
            <el-input
              v-model="f.site.brandName"
              maxlength="100"
              show-word-limit
              placeholder="示例：Sony"
              :class="{ 'lang-error': errors['site.brandName'] }"
              @input="onValidateSite('brandName', '品牌名')"
            />
            <div v-if="errors['site.brandName']" class="lang-error-hint">
              {{ errors["site.brandName"] }}
            </div>
          </el-form-item>
          <el-form-item label="包装尺寸" required>
            <div class="draft-field-row">
              <el-input
                v-model="f.site.packageLength"
                placeholder="75.50"
                class="draft-field-input--sm"
              />
              <el-input
                v-model="f.site.packageWidth"
                placeholder="10.00"
                class="draft-field-input--sm"
              />
              <el-input
                v-model="f.site.packageHeight"
                placeholder="50.00"
                class="draft-field-input--sm"
              />
              <el-select v-model="f.site.packageDimensionUnit" class="draft-field-input--md">
                <el-option label="Zentimeter" value="Zentimeter" />
                <el-option label="Inch" value="Inch" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="包裹重量" required>
            <div class="draft-field-row">
              <el-input
                v-model="f.site.packageWeight"
                placeholder="24"
                class="draft-field-input--sm"
              />
              <el-select v-model="f.site.packageWeightUnit" class="draft-field-input--sm">
                <el-option label="Pfund" value="Pfund" />
                <el-option label="Kilogramm" value="Kilogramm" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="销售类型" required>
            <el-radio-group v-model="f.site.salesType">
              <el-radio value="single">单体</el-radio>
              <el-radio value="variant">变体</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="配送渠道" required>
            <el-radio-group v-model="f.site.deliveryChannel">
              <el-radio value="FBA">FBA</el-radio>
              <el-radio value="FBM">FBM</el-radio>
            </el-radio-group>
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
          <el-form-item label="店铺" required>
            <el-select v-model="f.cn.shop" placeholder="请选择" class="draft-field-input--lg" />
          </el-form-item>
          <el-form-item label="上架类型" required>
            <el-radio-group v-model="f.cn.listingType">
              <el-radio value="new">创建新品</el-radio>
              <el-radio value="append">追加变体</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="Amazon分类" required>
            <el-input v-model="f.cn.amazonCategory" placeholder="例：软件 > 儿童与家庭" />
          </el-form-item>
          <el-form-item label="商品类型" required>
            <el-input v-model="f.cn.productType" placeholder="例：PHYSICAL_SOFTWARE" />
          </el-form-item>
          <el-form-item label="商品名称" required>
            <el-input
              v-model="f.cn.productName"
              type="textarea"
              :rows="2"
              maxlength="200"
              show-word-limit
              placeholder="示例：蓝色阿迪达斯运动鞋"
              :class="{ 'lang-error': errors['cn.productName'] }"
              @input="onValidateCn('productName', '商品名称')"
            />
            <div v-if="errors['cn.productName']" class="lang-error-hint">
              {{ errors["cn.productName"] }}
            </div>
          </el-form-item>
          <el-form-item label="商品亮点">
            <el-input
              v-model="f.cn.productHighlights"
              maxlength="125"
              show-word-limit
              placeholder="示例：透气材料"
              :class="{ 'lang-error': errors['cn.productHighlights'] }"
              @input="onValidateCn('productHighlights', '商品亮点')"
            />
            <div v-if="errors['cn.productHighlights']" class="lang-error-hint">
              {{ errors["cn.productHighlights"] }}
            </div>
          </el-form-item>
          <el-form-item label="品牌名" required>
            <el-input
              v-model="f.cn.brandName"
              maxlength="100"
              show-word-limit
              placeholder="示例：索尼"
              :class="{ 'lang-error': errors['cn.brandName'] }"
              @input="onValidateCn('brandName', '品牌名')"
            />
            <div v-if="errors['cn.brandName']" class="lang-error-hint">
              {{ errors["cn.brandName"] }}
            </div>
          </el-form-item>
          <el-form-item label="包装尺寸" required>
            <div class="draft-field-row">
              <el-input
                v-model="f.cn.packageLength"
                placeholder="75.50"
                class="draft-field-input--sm"
              />
              <el-input
                v-model="f.cn.packageWidth"
                placeholder="10.00"
                class="draft-field-input--sm"
              />
              <el-input
                v-model="f.cn.packageHeight"
                placeholder="50.00"
                class="draft-field-input--sm"
              />
              <el-select v-model="f.cn.packageDimensionUnit" class="draft-field-input--md">
                <el-option label="厘米" value="Zentimeter" />
                <el-option label="英寸" value="Inch" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="包裹重量" required>
            <div class="draft-field-row">
              <el-input
                v-model="f.cn.packageWeight"
                placeholder="24"
                class="draft-field-input--sm"
              />
              <el-select v-model="f.cn.packageWeightUnit" class="draft-field-input--sm">
                <el-option label="磅" value="Pfund" />
                <el-option label="千克" value="Kilogramm" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="销售类型" required>
            <el-radio-group v-model="f.cn.salesType">
              <el-radio value="single">单体</el-radio>
              <el-radio value="variant">变体</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="配送渠道" required>
            <el-radio-group v-model="f.cn.deliveryChannel">
              <el-radio value="FBA">FBA</el-radio>
              <el-radio value="FBM">FBM</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 基本信息 section：双栏布局（站点内容 / 中文内容）。
 * 语言相关字段（商品名称、商品亮点、品牌名）实时校验语言。
 *
 * 通过 inject 获取父组件 provide 的 formData / currentSiteCode / langErrors。
 */
import { inject } from "vue";
import type { ComputedRef } from "vue";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";

defineOptions({ name: "BasicInfoSection" });

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
