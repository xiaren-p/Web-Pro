<template>
  <div class="listing-filter">
    <el-form ref="queryFormRef" :model="queryParams" :inline="true" size="default">
      <!-- 国家 -->
      <el-form-item label="国家" prop="country">
        <el-select
          v-model="queryParams.country"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <!-- 全选选项 -->
          <el-option value="__ALL__" class="select-all-option">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllCountries"
                :indeterminate="isIndeterminateCountries"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option
            v-for="it in countryOptions"
            :key="it.value"
            :label="it.label"
            :value="it.value"
          >
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.country.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 店铺 -->
      <el-form-item label="店铺" prop="shopId" class="label-xs">
        <el-select
          v-model="queryParams.shopId"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <template #header>
            <div class="filter-shop-search">
              <el-input
                v-model="shopSearchKeyword"
                size="small"
                placeholder="搜索店铺"
                clearable
                :prefix-icon="Search"
                class="shop-filter-input"
              />
            </div>
          </template>
          <!-- 全选选项 -->
          <el-option value="__ALL__">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllShops"
                :indeterminate="isIndeterminateShops"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option v-for="it in shopOptions" :key="it.value" :label="it.label" :value="it.value">
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.shopId.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- Listing 状态 -->
      <el-form-item label="Listing状态" prop="listingStatus">
        <el-select
          v-model="queryParams.listingStatus"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <!-- 全选选项 -->
          <el-option value="__ALL__" class="select-all-option">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllListingStatus"
                :indeterminate="isIndeterminateListingStatus"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option
            v-for="it in listingStatusOptions"
            :key="it.value"
            :label="it.label"
            :value="it.value"
          >
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.listingStatus.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 配对状态 -->
      <el-form-item label="配对状态" prop="pairStatus">
        <el-select
          v-model="queryParams.pairStatus"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <!-- 全选选项 -->
          <el-option value="__ALL__" class="select-all-option">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllPairStatus"
                :indeterminate="isIndeterminatePairStatus"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option
            v-for="it in pairStatusOptions"
            :key="it.value"
            :label="it.label"
            :value="it.value"
          >
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.pairStatus.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 分类 -->
      <el-form-item label="分类" prop="categoryType">
        <el-select
          v-model="queryParams.categoryType"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <!-- 全选选项 -->
          <el-option value="__ALL__" class="select-all-option">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllCategoryTypes"
                :indeterminate="isIndeterminateCategoryTypes"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option
            v-for="it in categoryTypeOptions"
            :key="it.value"
            :label="it.label"
            :value="it.value"
          >
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.categoryType.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 负责人 -->
      <el-form-item label="负责人" prop="owner">
        <el-select
          v-model="queryParams.owner"
          placeholder="全部"
          clearable
          multiple
          collapse-tags
          collapse-tags-tooltip
          :max-collapse-tags="1"
          class="filter-select filter-select--md"
          @change="handleFilterChange"
        >
          <!-- 全选选项 -->
          <el-option value="__ALL__" class="select-all-option">
            <div class="filter-option">
              <el-checkbox
                :model-value="isAllOwners"
                :indeterminate="isIndeterminateOwners"
                class="filter-option__checkbox"
              />
              <span class="font-bold">全选</span>
            </div>
          </el-option>
          <el-option v-for="it in ownerOptions" :key="it.value" :label="it.label" :value="it.value">
            <div class="filter-option">
              <el-checkbox
                :model-value="queryParams.owner.includes(it.value)"
                class="filter-option__checkbox"
              />
              <span>{{ it.label }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 报表更新时间 -->
      <el-form-item label="新建时间" prop="reportUpdatedAt">
        <el-date-picker
          v-model="queryParams.reportUpdatedAt"
          :editable="false"
          type="daterange"
          range-separator="~"
          start-placeholder="开始日期"
          end-placeholder="截止日期"
          value-format="YYYY-MM-DD"
          class="filter-daterange"
          @change="handleFilterChange"
        />
      </el-form-item>

      <!-- 搜索行（关键字 + 重置） -->
      <el-form-item label="搜索" prop="keywords" class="search-row">
        <el-input
          v-model="displayKeywords"
          placeholder="输入关键字"
          clearable
          class="filter-search-input"
          @keyup.enter="handleQuery"
          @focus="searchInputFocused = true"
          @blur="searchInputFocused = false"
        >
          <template #prepend>
            <el-select
              v-model="queryParams.searchType"
              class="filter-search-type"
              @change="handleFilterChange"
            >
              <el-option
                v-for="it in searchTypeOptions"
                :key="it.value"
                :label="it.label"
                :value="it.value"
              />
            </el-select>
          </template>
          <template #suffix>
            <el-popover
              v-model:visible="multiSearchVisible"
              placement="bottom"
              :width="300"
              trigger="click"
            >
              <template #reference>
                <div class="filter-multi-trigger">
                  <el-tooltip content="多项搜索" :show-after="500" placement="top">
                    <el-icon class="filter-multi-trigger__icon" :size="16">
                      <Edit />
                    </el-icon>
                  </el-tooltip>
                </div>
              </template>
              <div>
                <el-input
                  v-model="multiSearchText"
                  type="textarea"
                  :rows="10"
                  placeholder="一行一项"
                />
                <div class="filter-multi-footer">
                  <el-button size="small" @click="handleMultiSearchClear">清空</el-button>
                  <el-button size="small" @click="multiSearchVisible = false">关闭</el-button>
                  <el-button size="small" type="primary" @click="handleMultiSearchConfirm">
                    搜索
                  </el-button>
                </div>
              </div>
            </el-popover>
          </template>
          <template #append>
            <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          </template>
        </el-input>
        <el-button class="ml-2" icon="refresh" @click="handleResetQuery">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
/**
 * Listing 列表搜索表单：与广告模块设计语言对齐的筛选区域。
 * 所属板块：listing。
 */
import { ref, computed, watch, inject } from "vue";
import { Search, Edit } from "@element-plus/icons-vue";

// Inject hooks from parent
const hooks: any = inject("listingHooks");
const {
  queryFormRef,
  queryParams,
  countryOptions,
  isAllCountries,
  isIndeterminateCountries,
  shopSearchKeyword,
  shopOptions,
  isAllShops,
  isIndeterminateShops,
  listingStatusOptions,
  isAllListingStatus,
  isIndeterminateListingStatus,
  pairStatusOptions,
  isAllPairStatus,
  isIndeterminatePairStatus,
  categoryTypeOptions,
  isAllCategoryTypes,
  isIndeterminateCategoryTypes,
  ownerOptions,
  isAllOwners,
  isIndeterminateOwners,
  searchTypeOptions,
  handleQuery,
  handleResetQuery,
  handleFilterChange,
} = hooks;

// 多项搜索相关
const multiSearchVisible = ref(false);
const multiSearchText = ref("");

watch(multiSearchVisible, (val) => {
  if (val) {
    if (queryParams.keywords) {
      // 将逗号分隔转换为换行显示
      multiSearchText.value = queryParams.keywords.replace(/,|，/g, "\n");
    } else {
      multiSearchText.value = "";
    }
  }
});

function handleMultiSearchClear() {
  multiSearchText.value = "";
}

function handleMultiSearchConfirm() {
  if (multiSearchText.value) {
    const lines = multiSearchText.value
      .split(/[\n\r]+/)
      .map((l) => l.trim())
      .filter(Boolean);
    queryParams.keywords = lines.join(","); // 用英文逗号连接
  } else {
    queryParams.keywords = "";
  }
  multiSearchVisible.value = false;
  handleQuery();
}

const searchInputFocused = ref(false);
const displayKeywords = computed({
  get: () => {
    const raw = queryParams.keywords;
    if (searchInputFocused.value) return raw;
    if (!raw) return "";
    if (raw.includes(",")) {
      const arr = raw.split(",").filter((s: string) => s.trim());
      if (arr.length > 1) {
        return `${arr[0]} +${arr.length - 1}`;
      }
    }
    return raw;
  },
  set: (val) => {
    queryParams.keywords = val;
  },
});
</script>

<style scoped lang="scss">
.listing-filter {
  /* 由外层 .content-block 提供卡片底色，内部仅控制表单节奏 */

  :deep(.el-form--inline .el-form-item) {
    margin-right: 16px;
    margin-bottom: 12px;
  }

  :deep(.el-form-item__label) {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-secondary);
  }
}

/* 通用 select 宽度 */
.filter-select--md {
  width: 140px;
}

/* 日期范围 */
.filter-daterange {
  width: 240px;
}

/* 关键字搜索行 */
.filter-search-input {
  width: 360px;
}

.filter-search-type {
  width: 80px;
}

/* 下拉选项内的 checkbox + 文字 */
.filter-option {
  display: flex;
  align-items: center;
}

.filter-option__checkbox {
  margin-right: 8px;
  pointer-events: none;
}

/* 店铺下拉的搜索条 */
.filter-shop-search {
  padding: 4px 6px;
  border-bottom: 1px solid var(--border-subtle);
}

/* 多项搜索弹层入口 */
.filter-multi-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  margin-right: 4px;
  cursor: pointer;
}

.filter-multi-trigger__icon {
  color: var(--text-tertiary);
  transition: color var(--transition-ui);
}

.filter-multi-trigger:hover .filter-multi-trigger__icon {
  color: var(--color-primary-600);
}

/* 多项搜索弹层底部按钮组 */
.filter-multi-footer {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>
