<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      基本信息
    </div>

    <!-- 共享字段：店铺 / 上架类型 / 分类 / 商品类型 -->
    <div class="draft-section__body basic-info__shared">
      <el-form label-position="left" label-width="200px" size="default">
        <el-form-item label="店铺" required>
          <el-select
            v-model="f.site.shop"
            v-loading="shopLoading"
            filterable
            placeholder="请选择店铺"
            class="basic-info__shop-select"
            @change="onShopChange"
          >
            <el-option
              v-for="shop in shopList"
              :key="shop.sid"
              :label="`${shop.name} (${shop.country})`"
              :value="shop.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="上架类型" required>
          <el-radio-group v-model="f.site.listingType">
            <el-radio value="new">创建新品</el-radio>
            <el-button
              v-if="f.site.listingType === 'new'"
              type="primary"
              link
              size="small"
              @click="showRefDialog = true"
            >
              引用商品
            </el-button>
            <el-radio value="append">追加变体</el-radio>
            <el-radio value="follow">创建跟卖</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Amazon分类" required>
          <span v-if="f.site.categoryPathName" class="basic-info__category-name">
            {{ f.site.categoryPathName }}
          </span>
          <el-button
            size="small"
            :disabled="!f.site.marketplaceId"
            @click="showCategoryDialog = true"
          >
            {{ f.site.categoryPathName ? "切换分类" : "选择分类" }}
          </el-button>
        </el-form-item>

        <el-form-item v-if="f.site.cateProductType.length" label="商品类型">
          <el-input
            :model-value="f.site.cateProductType.join(', ')"
            disabled
            class="basic-info__product-type"
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- 双栏文本字段 -->
    <el-row :gutter="24">
      <!-- 左栏：站点内容 -->
      <el-col :span="12">
        <div class="draft-col__header">站点内容</div>
        <div class="draft-section__body">
          <el-form label-position="left" label-width="200px" size="default">
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
        </div>
      </el-col>

      <!-- 右栏：中文内容 -->
      <el-col :span="12">
        <div class="draft-col__header">中文内容</div>
        <div class="draft-section__body">
          <el-form label-position="left" label-width="200px" size="default">
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
        </div>
      </el-col>
    </el-row>

    <!-- 分类选择弹窗 -->
    <CategorySelectDialog
      v-model:visible="showCategoryDialog"
      :marketplace-id="f.site.marketplaceId"
      @select="onCategorySelect"
    />

    <!-- 引用商品弹窗（占位） -->
    <el-dialog v-model="showRefDialog" title="引用商品" width="600px">
      <el-empty description="功能开发中" :image-size="80" />
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
/**
 * 基本信息 section。
 *
 * 上层共享字段（全宽）：店铺下拉、上架类型（3 radio + 引用商品入口）、Amazon 分类选择、商品类型回显。
 * 下层双栏字段：商品名称 / 商品亮点 / 品牌名 / 包装尺寸 / 包裹重量 / 销售类型 / 配送渠道。
 *
 * 店铺变更 -> 设 marketplaceId -> 重置分类。
 * 分类选中 -> 设 cateProductType -> 触发 useProductTypeSchema 拉取动态 Schema。
 * 文本字段实时校验语言（站点列校验站点语言，中文列校验中文）。
 */
import { ref, inject, onMounted } from "vue";
import type { ComputedRef } from "vue";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type { ShopOptionVO, AmazonCategoryVO } from "@/api/sales/listing-publish";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";
import CategorySelectDialog from "./components/CategorySelectDialog.vue";

defineOptions({ name: "BasicInfoSection" });

const f = inject<any>("draftForm");
const siteCode = inject<ComputedRef<string>>("currentSiteCode")!;
const errors = inject<Record<string, string>>("langErrors")!;

/** 店铺列表 + 加载状态 */
const shopList = ref<ShopOptionVO[]>([]);
const shopLoading = ref(false);

/** 弹窗状态 */
const showCategoryDialog = ref(false);
const showRefDialog = ref(false);

/** 加载店铺下拉列表 */
async function loadShopList() {
  shopLoading.value = true;
  try {
    shopList.value = await ListingPublishAPI.getShopOptions();
  } catch {
    shopList.value = [];
  } finally {
    shopLoading.value = false;
  }
}

/** 店铺变更：设 marketplaceId + mid，同步 cn，重置分类 */
function onShopChange(shopName: string) {
  const shop = shopList.value.find((s) => s.name === shopName);
  if (!shop) return;
  f.site.marketplaceId = shop.marketplaceId;
  f.site.mid = shop.mid;
  f.cn.shop = shopName;
  f.cn.marketplaceId = shop.marketplaceId;
  f.cn.mid = shop.mid;
  // 重置分类相关字段
  f.site.categoryUniqueId = "";
  f.site.categoryName = "";
  f.site.categoryPathName = "";
  f.site.cateProductType = [];
  f.site.productType = "";
  f.cn.categoryUniqueId = "";
  f.cn.categoryName = "";
  f.cn.categoryPathName = "";
  f.cn.cateProductType = [];
  f.cn.productType = "";
}

/** 分类选中：设分类信息 + productType，触发 Schema 拉取 */
function onCategorySelect(category: AmazonCategoryVO) {
  const {
    categoryUniqueId,
    categoryName,
    categoryPathName,
    productTypeOrigin,
    browseNodeAttributes,
  } = category;
  const displayPath = categoryPathName || categoryName;
  f.site.categoryUniqueId = categoryUniqueId;
  f.site.categoryName = displayPath;
  f.site.categoryPathName = displayPath;
  f.site.cateProductType = productTypeOrigin;
  f.site.productType = productTypeOrigin[0] || "";
  f.site.browseNodeAttributes = browseNodeAttributes;
  f.cn.categoryUniqueId = categoryUniqueId;
  f.cn.categoryName = displayPath;
  f.cn.categoryPathName = displayPath;
  f.cn.cateProductType = productTypeOrigin;
  f.cn.productType = productTypeOrigin[0] || "";
  f.cn.browseNodeAttributes = browseNodeAttributes;
}

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

onMounted(() => {
  loadShopList();
});
</script>

<style scoped lang="scss">
.basic-info {
  &__shared {
    margin-bottom: 16px;
  }

  &__shop-select {
    width: 320px;
  }

  &__category-name {
    margin-right: 12px;
    font-size: var(--font-size-sm);
    color: var(--text-primary);
  }

  &__product-type {
    width: 320px;
  }
}
</style>
