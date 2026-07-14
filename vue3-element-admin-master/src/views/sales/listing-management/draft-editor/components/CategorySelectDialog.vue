<template>
  <el-dialog
    :model-value="visible"
    title="选择分类"
    width="1000px"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
  >
    <!-- Tab 切换 -->
    <el-radio-group v-model="activeTab" class="category-dialog__tabs">
      <el-radio-button value="common">常用</el-radio-button>
      <el-radio-button value="search">搜索</el-radio-button>
      <el-radio-button value="browse">浏览</el-radio-button>
    </el-radio-group>

    <!-- Tab 1: 常用 -->
    <div v-if="activeTab === 'common'" class="category-dialog__panel">
      <el-empty v-if="!commonList.length" description="暂无常用分类" :image-size="60" />
      <div v-else class="category-dialog__list">
        <div v-for="item in commonList" :key="item.categoryUniqueId" class="category-dialog__item">
          <span class="category-dialog__item-name">
            {{ item.categoryPathName || item.categoryName }}
          </span>
          <span class="category-dialog__item-type">
            {{ item.productTypeOrigin?.join(", ") || "-" }}
          </span>
          <el-button v-if="isLeaf(item)" type="primary" size="small" @click="selectCategory(item)">
            选择
          </el-button>
        </div>
      </div>
    </div>

    <!-- Tab 2: 搜索 -->
    <div v-if="activeTab === 'search'" class="category-dialog__panel">
      <div class="category-dialog__search-bar">
        <el-select v-model="searchType" class="category-dialog__search-type" size="small">
          <el-option label="分类名称" value="category_name" />
          <el-option label="商品类型" value="product_type_origin" />
          <el-option label="分类ID" value="category_id" />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="输入关键词搜索"
          clearable
          size="small"
          class="category-dialog__search-input"
          @keyup.enter="doSearch"
        />
        <el-button type="primary" size="small" :loading="searchLoading" @click="doSearch">
          搜索
        </el-button>
      </div>
      <el-empty
        v-if="!searchLoading && !searchResults.length"
        description="输入关键词后搜索"
        :image-size="60"
      />
      <div v-else v-loading="searchLoading" class="category-dialog__list">
        <div
          v-for="item in searchResults"
          :key="item.categoryUniqueId"
          class="category-dialog__item"
        >
          <span class="category-dialog__item-name">
            {{ item.categoryPathName || item.categoryName }}
          </span>
          <span class="category-dialog__item-type">
            {{ item.productTypeOrigin?.join(", ") || "-" }}
          </span>
          <el-button v-if="isLeaf(item)" type="primary" size="small" @click="selectCategory(item)">
            选择
          </el-button>
        </div>
      </div>
    </div>

    <!-- Tab 3: 浏览 -->
    <div v-if="activeTab === 'browse'" class="category-dialog__panel">
      <!-- 面包屑 -->
      <div v-if="breadcrumb.length" class="category-dialog__breadcrumb">
        <span class="category-dialog__crumb" @click="goToLevel(-1)">全部</span>
        <template v-for="(crumb, idx) in breadcrumb" :key="idx">
          <span class="category-dialog__crumb-sep">></span>
          <span class="category-dialog__crumb" @click="goToLevel(idx)">
            {{ crumb.categoryName }}
          </span>
        </template>
      </div>
      <!-- 分类列表 -->
      <div v-loading="treeLoading" class="category-dialog__list">
        <el-empty
          v-if="!treeLoading && !currentList.length"
          description="暂无分类"
          :image-size="60"
        />
        <div
          v-for="item in currentList"
          :key="item.categoryUniqueId"
          class="category-dialog__item"
          :class="{ 'is-folder': item.hasChildren === 1 }"
        >
          <span class="category-dialog__item-name" @click="expandNode(item)">
            {{ item.categoryName }}
            <el-icon v-if="item.hasChildren === 1" class="category-dialog__arrow">
              <ArrowRight />
            </el-icon>
          </span>
          <template v-if="isLeaf(item)">
            <span class="category-dialog__item-type">
              {{ item.productTypeOrigin?.join(", ") || "-" }}
            </span>
            <el-button type="primary" size="small" @click="selectCategory(item)">选择</el-button>
          </template>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * Amazon 分类选择弹窗。
 *
 * 三个 Tab：
 * 1. 常用 - localStorage 读取最近 10 条选择记录
 * 2. 搜索 - 按分类名称 / 商品类型 / 分类ID 搜索
 * 3. 浏览 - 树形导航，点击有子分类的节点展开，叶子节点可选择
 *
 * 选中后 emit("select", categoryData) 并写入 localStorage 常用记录。
 *
 * 性能优化：
 * - rootCache / childrenCache 模块级 Map，会话内不重复请求
 * - watch(marketplaceId) 仅在弹窗打开时触发请求
 */
import { ref, watch } from "vue";
import { ArrowRight } from "@element-plus/icons-vue";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type { AmazonCategoryVO, CategorySearchType } from "@/api/sales/listing-publish";

interface Props {
  visible: boolean;
  marketplaceId: string;
}

interface Emits {
  "update:visible": [value: boolean];
  select: [category: AmazonCategoryVO];
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const activeTab = ref<"common" | "search" | "browse">("browse");

// ── 分类缓存（模块级，弹窗关闭不销毁）──
const rootCache = new Map<string, AmazonCategoryVO[]>();
const childrenCache = new Map<string, AmazonCategoryVO[]>();

/** 判断分类是否为叶子节点（不可再展开）。仿领星 selectItem 逻辑。 */
function isLeaf(item: AmazonCategoryVO): boolean {
  return item.hasChildren === 0 && item.childCategories.length === 0;
}
const STORAGE_KEY = "draftCategoryHistory";
const commonList = ref<AmazonCategoryVO[]>([]);

function loadCommonList() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    commonList.value = raw ? JSON.parse(raw) : [];
  } catch {
    commonList.value = [];
  }
}

function saveToCommon(category: AmazonCategoryVO) {
  const filtered = commonList.value.filter((c) => c.categoryUniqueId !== category.categoryUniqueId);
  filtered.unshift(category);
  commonList.value = filtered.slice(0, 10);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(commonList.value));
}

// ── 搜索 ──
const searchType = ref<CategorySearchType>("category_name");
const searchKeyword = ref("");
const searchLoading = ref(false);
const searchResults = ref<AmazonCategoryVO[]>([]);

async function doSearch() {
  if (!searchKeyword.value.trim() || !props.marketplaceId) return;
  searchLoading.value = true;
  try {
    searchResults.value = await ListingPublishAPI.searchCategories(
      props.marketplaceId,
      searchType.value,
      searchKeyword.value.trim()
    );
  } catch {
    searchResults.value = [];
  } finally {
    searchLoading.value = false;
  }
}

// ── 浏览 ──
const treeLoading = ref(false);
const currentList = ref<AmazonCategoryVO[]>([]);
const breadcrumb = ref<AmazonCategoryVO[]>([]);

async function loadRoot() {
  if (!props.marketplaceId) return;

  /** 命中缓存则直接使用，不发请求。 */
  const cached = rootCache.get(props.marketplaceId);
  if (cached) {
    currentList.value = cached;
    breadcrumb.value = [];
    return;
  }

  treeLoading.value = true;
  try {
    currentList.value = await ListingPublishAPI.getRootCategories(props.marketplaceId);
    rootCache.set(props.marketplaceId, currentList.value);
    breadcrumb.value = [];
  } catch {
    currentList.value = [];
  } finally {
    treeLoading.value = false;
  }
}

async function expandNode(node: AmazonCategoryVO) {
  if (node.hasChildren !== 1) return;

  /** 命中缓存则直接使用，不发请求。 */
  const cacheKey = `${props.marketplaceId}_${node.categoryUniqueId}`;
  const cached = childrenCache.get(cacheKey);
  if (cached) {
    breadcrumb.value.push(node);
    currentList.value = cached;
    return;
  }

  treeLoading.value = true;
  try {
    const children = await ListingPublishAPI.getCategoryChildren(
      props.marketplaceId,
      node.categoryUniqueId
    );
    breadcrumb.value.push(node);
    currentList.value = children;
    childrenCache.set(cacheKey, children);
  } catch {
    currentList.value = [];
  } finally {
    treeLoading.value = false;
  }
}

function goToLevel(idx: number) {
  if (idx === -1) {
    loadRoot();
  } else if (idx < breadcrumb.value.length - 1) {
    const target = breadcrumb.value[idx];
    breadcrumb.value = breadcrumb.value.slice(0, idx + 1);
    expandNode(target);
  }
}

// ── 选中分类 ──
function selectCategory(category: AmazonCategoryVO) {
  saveToCommon(category);
  emit("select", category);
  emit("update:visible", false);
}

/**
 * 弹窗打开时初始化：加载常用列表 + 根分类。
 * 仅在弹窗打开时触发，避免 marketplaceId 变更时在后台发起无效请求。
 */
watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadCommonList();
      if (activeTab.value === "browse") loadRoot();
    }
  }
);

watch(
  () => props.marketplaceId,
  () => {
    if (props.visible) loadRoot();
  }
);
</script>

<style scoped lang="scss">
.category-dialog {
  &__tabs {
    margin-bottom: 16px;
  }

  &__panel {
    min-height: 400px;
    max-height: 500px;
    overflow-y: auto;
  }

  &__search-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  &__search-type {
    width: 140px;
  }

  &__search-input {
    flex: 1;
  }

  &__breadcrumb {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
    padding: 8px 0 16px;
    font-size: var(--font-size-sm);
  }

  &__crumb {
    color: var(--color-primary-600);
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }

  &__crumb-sep {
    color: var(--text-tertiary);
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__item {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 10px 16px;
    background: var(--surface-subtle);
    border-radius: var(--radius-sm);

    &.is-folder {
      cursor: pointer;
    }
  }

  &__item-name {
    flex: 1;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
    cursor: pointer;
  }

  &__item-type {
    flex: 1;
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
  }

  &__arrow {
    margin-left: 4px;
    font-size: 12px;
    color: var(--text-tertiary);
  }
}
</style>
