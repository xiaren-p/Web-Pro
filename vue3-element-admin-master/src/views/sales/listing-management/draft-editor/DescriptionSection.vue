<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      描述
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
          <el-form-item label="产品描述" required>
            <el-input
              v-model="f.site.productDescription"
              type="textarea"
              :rows="6"
              maxlength="2000"
              show-word-limit
              :class="{ 'lang-error': errors['site.productDescription'] }"
              @input="onValidateSite('productDescription', '产品描述')"
            />
            <div v-if="errors['site.productDescription']" class="lang-error-hint">
              {{ errors["site.productDescription"] }}
            </div>
          </el-form-item>
          <el-form-item
            v-for="(_, idx) in f.site.bulletPoints"
            :key="idx"
            :label="idx === 0 ? '要点' : ''"
            required
          >
            <el-input
              v-model="f.site.bulletPoints[idx]"
              maxlength="700"
              show-word-limit
              placeholder="示例：Blumenmuster mit Blumenformen"
              :class="{ 'lang-error': errors[`site.bulletPoints.${idx}`] }"
              @input="onValidateSiteBullet(idx)"
            />
            <div v-if="errors[`site.bulletPoints.${idx}`]" class="lang-error-hint">
              {{ errors[`site.bulletPoints.${idx}`] }}
            </div>
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
          <el-form-item label="产品描述" required>
            <el-input
              v-model="f.cn.productDescription"
              type="textarea"
              :rows="6"
              maxlength="2000"
              show-word-limit
              :class="{ 'lang-error': errors['cn.productDescription'] }"
              @input="onValidateCn('productDescription', '产品描述')"
            />
            <div v-if="errors['cn.productDescription']" class="lang-error-hint">
              {{ errors["cn.productDescription"] }}
            </div>
          </el-form-item>
          <el-form-item
            v-for="(_, idx) in f.cn.bulletPoints"
            :key="idx"
            :label="idx === 0 ? '要点' : ''"
            required
          >
            <el-input
              v-model="f.cn.bulletPoints[idx]"
              maxlength="700"
              show-word-limit
              placeholder="示例：花朵图案，花朵形状"
              :class="{ 'lang-error': errors[`cn.bulletPoints.${idx}`] }"
              @input="onValidateCnBullet(idx)"
            />
            <div v-if="errors[`cn.bulletPoints.${idx}`]" class="lang-error-hint">
              {{ errors[`cn.bulletPoints.${idx}`] }}
            </div>
          </el-form-item>
        </el-form>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 描述 section：双栏布局（站点内容 / 中文内容）。
 * 产品描述 textarea（2000字上限）+ 5 条要点（各 700 字上限）。
 * 实时校验语言：站点列校验站点语言，中文列校验中文。
 *
 * 通过 inject 获取父组件 provide 的 formData / currentSiteCode / langErrors。
 */
import { inject } from "vue";
import type { ComputedRef } from "vue";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";

defineOptions({ name: "DescriptionSection" });

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

/** 校验站点要点 */
function onValidateSiteBullet(idx: number) {
  const key = `site.bulletPoints.${idx}`;
  const result = validateSiteLang(f.site.bulletPoints[idx], siteCode.value, `要点${idx + 1}`);
  errors[key] = result.message;
}

/** 校验中文要点 */
function onValidateCnBullet(idx: number) {
  const key = `cn.bulletPoints.${idx}`;
  const result = validateChinese(f.cn.bulletPoints[idx], `要点${idx + 1}`);
  errors[key] = result.message;
}
</script>
