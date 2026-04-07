<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true" size="small">
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
            style="width: 140px"
            @change="handleFilterChange"
          >
            <!-- 全选选项 -->
            <el-option value="__ALL__" class="select-all-option">
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllCountries"
                  :indeterminate="isIndeterminateCountries"
                  style="margin-right: 4px; pointer-events: none"
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
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.country.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
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
            style="width: 140px"
            @change="handleFilterChange"
          >
            <template #header>
              <div
                style="padding: 4px 6px; border-bottom: 1px solid var(--el-border-color-lighter)"
              >
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
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllShops"
                  :indeterminate="isIndeterminateShops"
                  style="margin-right: 4px; pointer-events: none"
                />
                <span class="font-bold">全选</span>
              </div>
            </el-option>
            <el-option
              v-for="it in shopOptions"
              :key="it.value"
              :label="it.label"
              :value="it.value"
            >
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.shopId.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
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
            style="width: 140px"
            @change="handleFilterChange"
          >
            <!-- 全选选项 -->
            <el-option value="__ALL__" class="select-all-option">
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllListingStatus"
                  :indeterminate="isIndeterminateListingStatus"
                  style="margin-right: 4px; pointer-events: none"
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
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.listingStatus.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
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
            style="width: 140px"
            @change="handleFilterChange"
          >
            <!-- 全选选项 -->
            <el-option value="__ALL__" class="select-all-option">
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllPairStatus"
                  :indeterminate="isIndeterminatePairStatus"
                  style="margin-right: 4px; pointer-events: none"
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
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.pairStatus.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
                />
                <span>{{ it.label }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <!-- 归类 -->
        <el-form-item label="归类" prop="categoryType">
          <el-select
            v-model="queryParams.categoryType"
            placeholder="全部"
            clearable
            multiple
            collapse-tags
            collapse-tags-tooltip
            :max-collapse-tags="1"
            style="width: 140px"
            @change="handleFilterChange"
          >
            <!-- 全选选项 -->
            <el-option value="__ALL__" class="select-all-option">
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllCategoryTypes"
                  :indeterminate="isIndeterminateCategoryTypes"
                  style="margin-right: 4px; pointer-events: none"
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
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.categoryType.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
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
            style="width: 140px"
            @change="handleFilterChange"
          >
            <!-- 全选选项 -->
            <el-option value="__ALL__" class="select-all-option">
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="isAllOwners"
                  :indeterminate="isIndeterminateOwners"
                  style="margin-right: 4px; pointer-events: none"
                />
                <span class="font-bold">全选</span>
              </div>
            </el-option>
            <el-option
              v-for="it in ownerOptions"
              :key="it.value"
              :label="it.label"
              :value="it.value"
            >
              <div class="flex-y-center">
                <el-checkbox
                  :model-value="queryParams.owner.includes(it.value)"
                  style="margin-right: 4px; pointer-events: none"
                />
                <span>{{ it.label }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <!-- 报表更新时间（置于第一列） -->
        <el-form-item label="新建时间" prop="reportUpdatedAt">
          <el-date-picker
            v-model="queryParams.reportUpdatedAt"
            :editable="false"
            type="daterange"
            range-separator="~"
            start-placeholder="开始日期"
            end-placeholder="截止日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
            @change="handleFilterChange"
          />
        </el-form-item>
        <!-- 搜索行（单独一行：搜索 + 重置） -->
        <el-form-item label="搜索" prop="keywords" class="search-row">
          <el-input
            v-model="displayKeywords"
            placeholder="输入关键字"
            clearable
            style="width: 360px"
            @keyup.enter="handleQuery"
            @focus="searchInputFocused = true"
            @blur="searchInputFocused = false"
          >
            <template #prepend>
              <el-select
                v-model="queryParams.searchType"
                style="width: 80px"
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
                  <div class="flex-center" style="height: 100%; margin-right: 4px; cursor: pointer">
                    <el-tooltip content="多项搜索" :show-after="500" placement="top">
                      <el-icon size="16" style="color: #909399"><Edit /></el-icon>
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
                  <div
                    style="
                      display: flex;
                      gap: 6px;
                      justify-content: flex-end;
                      margin-top: 10px;
                      text-align: right;
                    "
                  >
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

    <!-- 占位表格区域 -->
    <el-card shadow="hover" class="data-table">
      <div
        class="data-table__toolbar"
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 2px;
        "
      >
        <div class="data-table__toolbar--left">
          <el-button
            v-if="selectedRows.length > 0"
            type="primary"
            class="mr-2"
            size="small"
            @click="handleBatchOpen"
          >
            批量设置标签
          </el-button>
          <el-button
            v-if="selectedRows.length > 0"
            type="warning"
            class="mr-2"
            size="small"
            @click="handleBatchClassOpen"
          >
            批量设置归类
          </el-button>
        </div>
        <div class="data-table__toolbar--right">
          <el-tooltip content="列配置" placement="top">
            <el-button
              text
              icon="Setting"
              style="height: 22px; min-height: 22px; padding: 2px; font-size: 16px"
              @click="columnConfigVisible = true"
            />
          </el-tooltip>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        class="data-table__content"
        border
        height="100%"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" fixed="left" align="center" />
        <el-table-column v-for="col in tableColumns" :key="col.prop" v-bind="col">
          <template #default="scope">
            <!-- 图片 -->
            <template v-if="col.prop === 'image'">
              <el-popover placement="right" :width="220" trigger="hover" :show-after="500">
                <template #reference>
                  <div class="thumb-container">
                    <el-image :src="scope.row.image" fit="contain" class="thumb-img" lazy>
                      <template #error>
                        <div class="image-slot">
                          <el-icon><Picture /></el-icon>
                        </div>
                      </template>
                    </el-image>
                  </div>
                </template>
                <div style="text-align: center">
                  <img
                    v-if="scope.row.image"
                    :src="scope.row.image.replace(/_SL\d+_/, '_SL200_')"
                    style="max-width: 200px; max-height: 200px"
                  />
                </div>
              </el-popover>
            </template>

            <!-- MSKU -->
            <template v-else-if="col.prop === 'msku'">
              <div class="cell-text-container" @dblclick="handleCopy(scope.row.msku)">
                <el-tooltip
                  :content="scope.row.msku || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="!(scope.row.msku && scope.row.msku.length > 10)"
                >
                  <div class="text-ellipsis">{{ scope.row.msku || "-" }}</div>
                </el-tooltip>
                <el-tooltip
                  :content="scope.row.fnsku || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="!(scope.row.fnsku && scope.row.fnsku.length > 10)"
                >
                  <div class="color-#999 text-12px text-ellipsis">
                    {{ scope.row.fnsku || "-" }}
                  </div>
                </el-tooltip>
              </div>
            </template>
            <!-- 品名/SKU -->
            <template v-else-if="col.prop === 'skuName'">
              <div class="cell-text-container">
                <el-tooltip
                  :content="scope.row.skuName?.split('/')[0] || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="
                    !(
                      scope.row.skuName?.split('/')[0] &&
                      scope.row.skuName.split('/')[0].length > 10
                    )
                  "
                >
                  <div
                    class="text-ellipsis"
                    @dblclick="handleCopy(scope.row.skuName?.split('/')[0] || '')"
                  >
                    {{ scope.row.skuName?.split("/")[0] || "-" }}
                  </div>
                </el-tooltip>
                <el-tooltip
                  :content="scope.row.skuName?.split('/')[1] || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="
                    !(
                      scope.row.skuName?.split('/')[1] &&
                      scope.row.skuName.split('/')[1].length > 10
                    )
                  "
                >
                  <div
                    class="color-#999 text-12px text-ellipsis"
                    @dblclick="handleCopy(scope.row.skuName?.split('/')[1] || '')"
                  >
                    {{ scope.row.skuName?.split("/")[1] || "-" }}
                  </div>
                </el-tooltip>
              </div>
            </template>
            <!-- ASIN -->
            <template v-else-if="col.prop === 'asin'">
              <span @dblclick="handleCopy(scope.row.asin)">{{ scope.row.asin }}</span>
            </template>
            <!-- 父ASIN -->
            <template v-else-if="col.prop === 'parentAsin'">
              <span @dblclick="handleCopy(scope.row.parentAsin)">{{ scope.row.parentAsin }}</span>
            </template>

            <!-- 状态 -->
            <template v-else-if="col.prop === 'status'">
              <el-tag v-if="scope.row.status === 'on'" type="success">在售</el-tag>
              <el-tag v-else-if="scope.row.status === 'off'" type="info">停售</el-tag>
              <el-tag v-else-if="scope.row.status === 'draft'" type="warning">草稿</el-tag>
              <el-tag v-else-if="scope.row.status === 'deleted'" type="danger">已删除</el-tag>
            </template>

            <!-- 节气标签 -->
            <template v-else-if="col.prop === 'solarTermTags'">
              <div
                class="cursor-pointer"
                style="
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  min-height: 24px;
                "
                @click="handleEditTags(scope.row)"
              >
                <template v-if="asinTagsMap[scope.row.asin]?.length">
                  <el-tag
                    size="small"
                    effect="plain"
                    style="
                      max-width: 70px;
                      overflow: hidden;
                      text-overflow: ellipsis;
                      white-space: nowrap;
                    "
                  >
                    {{ asinTagsMap[scope.row.asin][0] }}
                  </el-tag>
                  <el-tag
                    v-if="asinTagsMap[scope.row.asin].length > 1"
                    size="small"
                    type="info"
                    effect="plain"
                    class="ml-1"
                  >
                    +{{ asinTagsMap[scope.row.asin].length - 1 }}
                  </el-tag>
                </template>
                <el-icon v-else class="text-gray-400"><Edit /></el-icon>
              </div>
            </template>

            <!-- 标题 (特殊处理 showOverflowTooltip 参数) -->
            <template v-else-if="col.prop === 'title'">
              <el-tooltip
                :content="scope.row.title"
                placement="top"
                :show-after="500"
                :disabled="!scope.row.title"
              >
                <div class="text-ellipsis" @dblclick="handleCopy(scope.row.title)">
                  {{ scope.row.title }}
                </div>
              </el-tooltip>
            </template>

            <!-- 大类排名 (优化：双列显示) -->
            <template v-else-if="col.prop === 'rank'">
              <div
                v-if="scope.row.rank && scope.row.rank.rank"
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-start;
                  line-height: 1.3;
                "
              >
                <span style="font-weight: bold">
                  {{ scope.row.rank.rank }}
                </span>
                <el-tooltip
                  :content="scope.row.rank.category || ''"
                  placement="top"
                  :show-after="500"
                  :disabled="!scope.row.rank.category"
                >
                  <span class="text-ellipsis" style="width: 100%">
                    {{ scope.row.rank.category }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 小类排名 (特殊双列显示 + Tooltip) -->
            <template v-else-if="col.prop === 'smallRank'">
              <div
                v-if="scope.row.smallRank && scope.row.smallRank.length > 0"
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-start;
                  line-height: 1.3;
                "
              >
                <span style="font-weight: bold">
                  {{ scope.row.smallRank[0].rank }}
                </span>
                <el-tooltip
                  :content="scope.row.smallRank[0].category"
                  placement="top"
                  :show-after="500"
                >
                  <span class="text-ellipsis" style="width: 100%">
                    {{ scope.row.smallRank[0].category }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 评分 (复刻样式：星级+分数一行，总数下一行，靠右) -->
            <template v-else-if="col.prop === 'rating'">
              <div
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-end;
                  line-height: 1.2;
                "
              >
                <!-- 第一行：星星 + 评分值 -->
                <div class="flex-y-center" style="justify-content: flex-end">
                  <div style="position: relative; width: 70px; height: 14px; margin-right: 4px">
                    <div style="display: flex; width: 100%; height: 100%">
                      <el-icon v-for="i in 5" :key="'bg-' + i" :size="14" color="#EFF2F7">
                        <StarFilled />
                      </el-icon>
                    </div>
                    <div
                      :style="{
                        width: (scope.row.rating.value / 5) * 100 + '%',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                      }"
                    >
                      <el-icon v-for="i in 5" :key="'fg-' + i" :size="14" color="#F7BA2A">
                        <StarFilled />
                      </el-icon>
                    </div>
                  </div>
                  <span style="font-size: 12px; color: #f7ba2a">{{ scope.row.rating.value }}</span>
                </div>
                <!-- 第二行：总数 -->
                <span style="margin-top: 2px; font-size: 12px; color: #606266">
                  {{ scope.row.rating.count }}
                </span>
              </div>
            </template>

            <!-- 操作 -->
            <template v-else-if="col.prop === 'operation'">
              <el-button type="primary" text size="small" disabled>查看</el-button>
              <el-button type="primary" text size="small" disabled>编辑</el-button>
            </template>

            <!-- 默认展示 -->
            <span v-else>{{ scope.row[col.prop] }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex-x-end" style="margin-top: -12px">
        <el-pagination
          size="small"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="pageNum"
          :page-size="pageSize"
          :page-sizes="[50, 100, 200]"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 列配置组件 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="columns"
      @save="handleConfigSave"
      @reset="handleConfigReset"
    />

    <!-- 节气标签编辑弹窗 -->
    <el-dialog
      v-model="batchTagDialogVisible"
      title="批量设置节气标签"
      width="400px"
      append-to-body
    >
      <div>
        <div style="margin-bottom: 15px; font-size: 14px; color: #909399">
          输入标签后回车确认，可输入多个。
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px">
          <el-tag
            v-for="tag in batchTags"
            :key="tag"
            closable
            :disable-transitions="false"
            @close="handleBatchRemoveTag(tag)"
          >
            {{ tag }}
          </el-tag>
          <el-input
            v-if="batchInputVisible"
            ref="batchInputRef"
            v-model="batchInput"
            size="small"
            style="width: 100px"
            @keyup.enter="handleBatchInputConfirm"
            @blur="handleBatchInputConfirm"
          />
          <el-button v-else size="small" @click="showBatchInput">+ New Tag</el-button>
        </div>
      </div>
      <template #footer>
        <div style="display: flex; justify-content: space-between">
          <div>
            <el-button @click="handleBatchClear">清空</el-button>
            <el-button @click="batchTagDialogVisible = false">返回</el-button>
          </div>
          <div>
            <el-button type="danger" @click="confirmBatchAction('delete')">删除</el-button>
            <el-button type="primary" @click="confirmBatchAction('add')">添加</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 节气标签编辑弹窗 -->
    <el-dialog v-model="tagDialogVisible" title="编辑节气标签" width="400px" append-to-body>
      <div>
        <div style="margin-bottom: 15px; font-size: 14px; color: #909399">
          ASIN: {{ currentTagAsin }}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px">
          <el-tag v-for="tag in currentTags" :key="tag" closable @close="handleRemoveTag(tag)">
            {{ tag }}
          </el-tag>
          <el-input
            v-if="inputVisible"
            ref="inputRef"
            v-model="newTagInput"
            style="width: 100px"
            size="small"
            @keyup.enter="handleInputConfirm"
            @blur="handleInputConfirm"
          />
          <el-button v-else size="small" @click="showInput">+ New Tag</el-button>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tagDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveTags">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 批量归类弹窗 -->
    <el-dialog v-model="batchClassDialogVisible" title="批量设置归类" width="400px" append-to-body>
      <div style="padding: 20px 0">
        <el-form label-width="80px">
          <el-form-item label="归类类型">
            <el-select v-model="batchClassValue" placeholder="请选择归类" style="width: 100%">
              <el-option
                v-for="item in categoryTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div style="display: flex; justify-content: flex-end">
          <el-button @click="batchClassDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleBatchClassConfirm">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  ShopsAPI,
  SalesProductListingAPI,
  SolarTermTagAPI,
  ProductClassificationAPI,
  type ListingItemVO,
} from "@/backend";
import ColumnManager from "./components/ColumnManager.vue";
import useClipboard from "vue-clipboard3";
import { Edit, Search } from "@element-plus/icons-vue";

defineOptions({ name: "SalesProductListing" });

const { toClipboard } = useClipboard();
const queryFormRef = ref();
const loading = ref(false);
const columnConfigVisible = ref(false);

const asinTagsMap = ref<Record<string, string[]>>({});

// 批量操作相关
const selectedRows = ref<ListingItemVO[]>([]);
const batchTagDialogVisible = ref(false);
const batchTags = ref<string[]>([]);
const batchInput = ref("");
const batchInputVisible = ref(false);
const batchInputRef = ref();

function handleSelectionChange(selection: ListingItemVO[]) {
  selectedRows.value = selection;
}

function handleBatchOpen() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选商品");
    return;
  }
  batchTags.value = [];
  batchInput.value = "";
  batchTagDialogVisible.value = true;
}

function showBatchInput() {
  batchInputVisible.value = true;
  nextTick(() => {
    batchInputRef.value?.focus();
  });
}

function handleBatchInputConfirm() {
  const val = batchInput.value.trim();
  if (val) {
    if (!batchTags.value.includes(val)) {
      batchTags.value.push(val);
    }
  }
  batchInputVisible.value = false;
  batchInput.value = "";
}

function handleBatchRemoveTag(tag: string) {
  batchTags.value = batchTags.value.filter((t) => t !== tag);
}

function handleBatchClear() {
  batchTags.value = [];
}

function confirmBatchAction(action: "add" | "delete") {
  if (batchTags.value.length === 0) {
    ElMessage.warning("请先输入标签");
    return;
  }
  const actionText = action === "add" ? "添加" : "删除";
  ElMessageBox.confirm(
    `确定要对选中的 ${selectedRows.value.length} 个商品${actionText}以下标签吗？\n${batchTags.value.join(", ")}`,
    "确认操作",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).then(() => {
    executeBatchAction(action);
  });
}

async function executeBatchAction(action: "add" | "delete") {
  const updates: any[] = [];
  // 遍历选中行，计算新的标签集合
  for (const row of selectedRows.value) {
    // 确保使用最新的 asinTagsMap 数据
    const originalTags = asinTagsMap.value[row.asin] || [];
    let newTags = [...originalTags];

    if (action === "add") {
      // 合并去重
      const set = new Set([...newTags, ...batchTags.value]);
      newTags = Array.from(set);
    } else {
      // 移除
      newTags = newTags.filter((t) => !batchTags.value.includes(t));
    }

    updates.push({
      asin: row.asin,
      tags: newTags,
    });
  }

  try {
    await SolarTermTagAPI.upsert(updates);
    ElMessage.success("批量操作成功");

    // 更新本地缓存
    updates.forEach((u) => {
      asinTagsMap.value[u.asin] = u.tags;
    });

    batchTagDialogVisible.value = false;
  } catch (e) {
    console.error(e);
    ElMessage.error("操作失败");
  }
}

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
    // 判断是否包含逗号
    if (raw.includes(",")) {
      const arr = raw.split(",").filter((s) => s.trim());
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

// 节气标签相关逻辑
const tagDialogVisible = ref(false);
// 当前操作的 ASIN
const currentTagAsin = ref("");
// 当前编辑的标签副本
const currentTags = ref<string[]>([]);
const newTagInput = ref("");
const inputVisible = ref(false);
const inputRef = ref();

function handleEditTags(row: ListingItemVO) {
  currentTagAsin.value = row.asin;
  currentTags.value = [...(asinTagsMap.value[row.asin] || [])];
  tagDialogVisible.value = true;
}

function showInput() {
  inputVisible.value = true;
  nextTick(() => {
    const el = inputRef.value;
    if (el) {
      if (el.input?.focus) {
        el.input.focus();
      } else {
        el.focus?.();
      }
    }
  });
}

function handleInputConfirm() {
  const val = newTagInput.value.trim();
  if (val) {
    if (!currentTags.value.includes(val)) {
      currentTags.value.push(val);
    }
  }
  inputVisible.value = false;
  newTagInput.value = "";
}

function handleRemoveTag(tag: string) {
  currentTags.value = currentTags.value.filter((t) => t !== tag);
}

function handleSaveTags() {
  SolarTermTagAPI.upsert({
    asin: currentTagAsin.value,
    tags: currentTags.value,
  }).then(() => {
    ElMessage.success("保存成功");
    asinTagsMap.value[currentTagAsin.value] = [...currentTags.value];
    tagDialogVisible.value = false;
  });
}

// 批量归类相关
const batchClassDialogVisible = ref(false);
const batchClassValue = ref(""); // 选中的类型

function handleBatchClassOpen() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选商品");
    return;
  }
  batchClassValue.value = "";
  batchClassDialogVisible.value = true;
}

function handleBatchClassConfirm() {
  if (!batchClassValue.value) {
    ElMessage.warning("请选择分类");
    return;
  }

  ElMessageBox.confirm(
    `确定要将选中的 ${selectedRows.value.length} 个商品归类设置为【${batchClassValue.value}】吗？`,
    "确认操作",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).then(() => {
    executeBatchClass();
  });
}

async function executeBatchClass() {
  const data = selectedRows.value.map((row) => ({
    msku: row.seller_sku,
    sku: row.local_sku,
    classification_type: batchClassValue.value,
  }));

  try {
    await ProductClassificationAPI.upsert(data);
    ElMessage.success("设置成功");
    batchClassDialogVisible.value = false;
    // 刷新列表
    handleQuery();
  } catch (e) {
    console.error(e);
    ElMessage.error("设置失败");
  }
}

// 复制功能
const handleCopy = async (text: string) => {
  if (!text) return;
  try {
    await toClipboard(text);
    ElMessage.success("复制成功");
  } catch {
    ElMessage.error("复制失败");
  }
};

// 默认列配置
const defaultColumns = [
  {
    prop: "image",
    label: "图片",
    visible: true,
    fixed: "left",
    width: 69,
    align: "center",
    category: "基础信息",
  },
  {
    prop: "msku",
    label: "MSKU/FNSKU",
    visible: true,
    fixed: "left",
    width: 150,
    category: "基础信息",
    sortable: "custom",
  },
  {
    prop: "skuName",
    label: "品名/SKU",
    visible: true,
    fixed: "left",
    width: 150,
    category: "基础信息",
    sortable: "custom",
  },
  { prop: "shop", label: "店铺", visible: true, width: 114, category: "基础信息" },
  { prop: "country", label: "国家", visible: true, width: 75, category: "基础信息" },
  {
    prop: "status",
    label: "状态",
    visible: true,
    fixed: false,
    width: 90,
    align: "center",
    category: "基础信息",
  },
  {
    prop: "createTime",
    label: "创建时间",
    visible: true,
    width: 185,
    category: "其他信息",
    sortable: "custom",
  },
  { prop: "asin", label: "ASIN", visible: true, fixed: false, width: 120, category: "基础信息" },
  { prop: "parentAsin", label: "父ASIN", visible: true, width: 120, category: "基础信息" },
  {
    prop: "title",
    label: "标题",
    visible: true,
    fixed: false,
    width: 174,
    showOverflowTooltip: false, // 改为手动控制 tooltip
    category: "基础信息",
  },
  { prop: "classification", label: "归类", visible: true, width: 100, category: "基础信息" },
  {
    prop: "solarTermTags",
    label: "节气标签",
    visible: true,
    width: 120,
    align: "center",
    category: "基础信息",
  },
  { prop: "price", label: "价格", visible: true, width: 80, align: "right", category: "库存价格" },
  {
    prop: "totalPrice",
    label: "售价(总价)",
    visible: true,
    width: 85,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "discountPrice",
    label: "优惠价",
    visible: true,
    width: 80,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "fbaSellable",
    label: "FBA可售",
    visible: true,
    width: 80,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "estFbaFee",
    label: "预估FBA费",
    visible: true,
    width: 85,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "referralFee",
    label: "平台费",
    visible: true,
    width: 80,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "salesToday",
    label: "今日销量",
    visible: true,
    width: 100,
    align: "right",
    category: "销售数据",
    sortable: "custom",
  },
  {
    prop: "salesYesterday",
    label: "昨日销量",
    visible: true,
    width: 100,
    align: "right",
    category: "销售数据",
    sortable: "custom",
  },
  {
    prop: "sales7_14_30",
    label: "7|14|30天销量",
    visible: true,
    width: 150,
    align: "center",
    category: "销售数据",
  },
  {
    prop: "rank",
    label: "大类排名",
    visible: true,
    width: 150,
    align: "left",
    category: "销售数据",
    sortable: "custom",
  },
  {
    prop: "profit",
    label: "订单毛利率/毛利润",
    visible: true,
    width: 180,
    align: "right",
    category: "销售数据",
    sortable: "custom",
  },
  { prop: "salesTrend", label: "销量趋势图", visible: true, width: 150, category: "销售数据" },
  {
    prop: "avgSales7_14_30",
    label: "7|14|30日均销量",
    visible: true,
    width: 150,
    align: "center",
    category: "销售数据",
  },
  {
    prop: "salesAmountYesterday",
    label: "昨日销售额",
    visible: true,
    width: 120,
    align: "right",
    category: "销售数据",
  },
  {
    prop: "salesAmount7_14_30",
    label: "7|14|30天销售额",
    visible: true,
    width: 200,
    align: "center",
    category: "销售数据",
  },
  {
    prop: "adCostYesterday",
    label: "昨日广告费",
    visible: true,
    width: 120,
    align: "right",
    category: "销售数据",
    sortable: "custom",
  },
  {
    prop: "adCost7_14_30",
    label: "7|14|30天广告费",
    visible: true,
    width: 200,
    align: "center",
    category: "销售数据",
  },
  {
    prop: "smallRank",
    label: "小类排名",
    visible: true,
    width: 150,
    align: "left",
    category: "销售数据",
    sortable: "custom",
  },
  {
    prop: "rating",
    label: "评分/Rating总数",
    visible: true,
    width: 140,
    align: "right",
    category: "销售数据",
  },
  {
    prop: "openTime",
    label: "开售时间",
    visible: true,
    width: 150,
    category: "其他信息",
    sortable: "custom",
  },
  {
    prop: "firstOrderTime",
    label: "首单时间",
    visible: true,
    width: 110,
    category: "其他信息",
    sortable: "custom",
  },
  { prop: "pairType", label: "配对方式", visible: true, width: 100, category: "其他信息" },
  { prop: "owner", label: "负责人", visible: true, width: 80, category: "其他信息" },
  { prop: "remarks", label: "备注", visible: true, width: 150, category: "其他信息" },
  {
    prop: "operation",
    label: "操作",
    visible: true,
    fixed: "right",
    width: 160,
    align: "center",
    category: "基础信息",
  },
  // 补充 test.html 中的其他列（默认隐藏）
  { prop: "analysis", label: "分析", visible: false, width: 80, category: "基础信息" },
  { prop: "fulfillment", label: "配送方式", visible: false, width: 90, category: "基础信息" },
  { prop: "brand", label: "亚马逊品牌", visible: false, width: 99, category: "基础信息" },
  { prop: "productCode", label: "商品编码", visible: false, width: 100, category: "基础信息" },
  { prop: "variants", label: "变体属性", visible: false, width: 100, category: "基础信息" },
  { prop: "localBrand", label: "本地品牌", visible: false, width: 100, category: "基础信息" },
  {
    prop: "b2bPrice",
    label: "B2B价格",
    visible: false,
    width: 100,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "listPrice",
    label: "List Price",
    visible: false,
    width: 100,
    align: "right",
    category: "库存价格",
  },
  {
    prop: "fbmStock",
    label: "FBM库存",
    visible: false,
    width: 100,
    align: "right",
    category: "库存价格",
  },
];

const STORAGE_KEY = "SALES_PRODUCT_LISTING_COLUMNS_V4";

// 初始化列配置（合并本地缓存）
const initColumns = () => {
  const cached = localStorage.getItem(STORAGE_KEY);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      // 合并策略：保留缓存的顺序和状态，同步最新的元数据(category/label)，并剔除已废弃的列
      const defaultMap = new Map(defaultColumns.map((c) => [c.prop, c]));
      const cachedProps = new Set();

      const merged = parsed
        .map((c: any) => {
          const def = defaultMap.get(c.prop);
          if (def) {
            cachedProps.add(c.prop);
            return { ...c, category: def.category, label: def.label };
          }
          return null;
        })
        .filter(Boolean);

      const newCols = defaultColumns.filter((c) => !cachedProps.has(c.prop));
      return [...merged, ...newCols];
    } catch (e) {
      console.error("读取列配置失败", e);
    }
  }
  return JSON.parse(JSON.stringify(defaultColumns));
};

const columns = ref(initColumns());

// 仅获取可见列，用于表格渲染
const tableColumns = computed(() => columns.value.filter((c: any) => c.visible));

function handleConfigSave(newColumns: any[]) {
  columns.value = newColumns;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns));
  ElMessage.success("配置已保存");
}
function handleConfigReset() {
  columns.value = JSON.parse(JSON.stringify(defaultColumns));
  localStorage.removeItem(STORAGE_KEY);
  ElMessage.success("已恢复默认配置");
}

// 查询参数
const queryParams = reactive({
  country: [] as string[],
  shopId: [] as string[],
  listingStatus: [] as string[],
  pairStatus: [] as string[],
  categoryType: [] as string[],
  owner: [] as string[],
  reportUpdatedAt: undefined as [string, string] | undefined,
  searchType: "sku" as "seller_sku" | "asin" | "sku",
  keywords: "",
  // 新增排序参数
  sort: undefined as string | undefined,
  order: undefined as string | null | undefined, // ascending, descending, null
});

// 店铺原始数据
const shopListRaw = ref<any[]>([]);

// 动态计算国家选项
const countryOptions = computed(() => {
  const countries = new Set<string>();
  shopListRaw.value.forEach((s) => {
    if (s.country) countries.add(s.country);
  });
  // 多选模式下移除“全部”选项，空数组即代表全部
  const list: { label: string; value: string }[] = [];
  Array.from(countries)
    .sort()
    .forEach((c) => {
      list.push({ label: c, value: c });
    });
  return list;
});

// 计算所有有效的国家值
const allCountryValues = computed(() => countryOptions.value.map((it) => it.value));
// 判断国家是否全选
const isAllCountries = computed(() => {
  const selected = queryParams.country;
  const all = allCountryValues.value;
  return all.length > 0 && selected.length === all.length;
});
// 判断国家是否半选
const isIndeterminateCountries = computed(() => {
  const len = queryParams.country.length;
  return len > 0 && len < allCountryValues.value.length;
});

// 动态计算店铺选项（根据选中的国家筛选）
const shopSearchKeyword = ref("");

// 基础店铺选项 (仅国家过滤)
const baseShopOptions = computed(() => {
  let list = shopListRaw.value;
  // 如果选择了国家（数组非空），则进行筛选
  if (queryParams.country && queryParams.country.length > 0) {
    list = list.filter((s) => queryParams.country.includes(s.country));
  }
  const options: { label: string; value: string }[] = [];
  list.forEach((s) => {
    options.push({ label: s.label || s.name, value: s.id });
  });
  return options;
});

// 最终展示选项 (搜索过滤)
const shopOptions = computed(() => {
  const options = baseShopOptions.value;
  if (!shopSearchKeyword.value) return options;
  const kw = shopSearchKeyword.value.trim().toLowerCase();
  return options.filter((o) => o.label.toLowerCase().includes(kw));
});

// 计算所有有效的店铺值 (基于当前筛选结果)
const allShopValues = computed(() => shopOptions.value.map((it) => it.value));
// 判断店铺是否全选 (基于当前筛选结果)
const isAllShops = computed(() => {
  const selected = queryParams.shopId;
  const all = allShopValues.value;
  if (all.length === 0) return false;
  return all.every((id) => selected.includes(id));
});
// 判断店铺是否半选 (基于当前筛选结果)
const isIndeterminateShops = computed(() => {
  const selected = queryParams.shopId;
  const all = allShopValues.value;
  if (all.length === 0) return false;
  // 计算选中了多少个当前可见的
  const selectedCount = all.filter((id) => selected.includes(id)).length;
  return selectedCount > 0 && selectedCount < all.length;
});

// 监听国家变化，过滤已选的店铺 + 处理全选逻辑
watch(
  () => queryParams.country,
  (newVal) => {
    // 处理全选点击 (包含 __ALL__ 的情况)
    if (newVal.includes("__ALL__")) {
      // 移除 __ALL__ 标记
      const realValues = newVal.filter((v) => v !== "__ALL__");
      // 如果之前不是全选，则变为全选；如果之前是全选（理论上此时点全选，数组会变长，但逻辑上我们视作反选操作或者强制全选）
      // 这里的交互逻辑：点击“全选”Item -> 触发变更。
      // 如果当前真实选中的数量 等于 总数量（说明之前就是全选），则清空。
      // 否则（说明之前是部分选或未选），则全选。
      if (realValues.length === allCountryValues.value.length) {
        queryParams.country = [];
      } else {
        queryParams.country = [...allCountryValues.value];
      }
      return;
    }

    // 正常的过滤逻辑
    if (newVal && newVal.length > 0) {
      // 获取当前符合条件的店铺 ID 集合
      // 注意：这里需要重新基于新的 countryOptions 计算 shopOptions（computed 会自动更新，但在这里我们要获取的是更新后的）
      // 由于 computed 更新也是响应式的，这里直接用逻辑推算一下安全的 shop list
      const currentCountryCodes = newVal;
      const validShops = shopListRaw.value.filter((s) => currentCountryCodes.includes(s.country));
      const validShopIds = validShops.map((s) => s.id);

      // 保留那些仍然有效的已选店铺
      queryParams.shopId = queryParams.shopId.filter((id) => validShopIds.includes(id));
    }
  },
  { deep: true } // 数组监听建议加 deep，虽然这里引用变化也会触发
);

// 监听店铺变化，处理全选逻辑
watch(
  () => queryParams.shopId,
  (newVal) => {
    if (newVal.includes("__ALL__")) {
      const realValues = newVal.filter((v) => v !== "__ALL__");
      // 获取当前筛选后的所有选项值
      const visibleValues = allShopValues.value;

      // 判断 visibleValues 是否都已经选中
      const isAllVisibleSelected =
        visibleValues.length > 0 && visibleValues.every((id) => realValues.includes(id));

      if (isAllVisibleSelected) {
        // 反选：移除所有当前可见的
        queryParams.shopId = realValues.filter((id) => !visibleValues.includes(id));
      } else {
        // 全选：合并当前可见的
        const newSet = new Set([...realValues, ...visibleValues]);
        queryParams.shopId = Array.from(newSet);
      }
    }
  }
);

const listingStatusOptions = [
  { label: "在售", value: "on" },
  { label: "停售", value: "off" },
  { label: "已删除", value: "deleted" },
];
// listingStatus 全选逻辑
const allListingStatusValues = listingStatusOptions.map((it) => it.value);
const isAllListingStatus = computed(() => {
  const selected = queryParams.listingStatus;
  const all = allListingStatusValues;
  return all.length > 0 && selected.length === all.length;
});
const isIndeterminateListingStatus = computed(() => {
  const len = queryParams.listingStatus.length;
  return len > 0 && len < allListingStatusValues.length;
});
watch(
  () => queryParams.listingStatus,
  (newVal) => {
    if (newVal.includes("__ALL__")) {
      const realValues = newVal.filter((v) => v !== "__ALL__");
      if (realValues.length === allListingStatusValues.length) {
        queryParams.listingStatus = [];
      } else {
        queryParams.listingStatus = [...allListingStatusValues];
      }
    }
  }
);

const pairStatusOptions = [
  { label: "已配对", value: "paired" },
  { label: "未配对", value: "unpaired" },
];
// pairStatus 全选逻辑
const allPairStatusValues = pairStatusOptions.map((it) => it.value);
const isAllPairStatus = computed(() => {
  const selected = queryParams.pairStatus;
  const all = allPairStatusValues;
  return all.length > 0 && selected.length === all.length;
});
const isIndeterminatePairStatus = computed(() => {
  const len = queryParams.pairStatus.length;
  return len > 0 && len < allPairStatusValues.length;
});
watch(
  () => queryParams.pairStatus,
  (newVal) => {
    if (newVal.includes("__ALL__")) {
      const realValues = newVal.filter((v) => v !== "__ALL__");
      if (realValues.length === allPairStatusValues.length) {
        queryParams.pairStatus = [];
      } else {
        queryParams.pairStatus = [...allPairStatusValues];
      }
    }
  }
);

const categoryTypeOptions = [
  { label: "饰品", value: "饰品" },
  { label: "普货", value: "普货" },
  { label: "正常服装", value: "正常服装" },
  { label: "情趣服装", value: "情趣服装" },
  { label: "其他", value: "其他" },
  { label: "无", value: "无" },
];
// categoryType 全选逻辑
const allCategoryTypeValues = categoryTypeOptions.map((it) => it.value);
const isAllCategoryTypes = computed(() => {
  const selected = queryParams.categoryType;
  const all = allCategoryTypeValues;
  return all.length > 0 && selected.length === all.length;
});
const isIndeterminateCategoryTypes = computed(() => {
  const len = queryParams.categoryType.length;
  return len > 0 && len < allCategoryTypeValues.length;
});
watch(
  () => queryParams.categoryType,
  (newVal) => {
    if (newVal.includes("__ALL__")) {
      const realValues = newVal.filter((v) => v !== "__ALL__");
      if (realValues.length === allCategoryTypeValues.length) {
        queryParams.categoryType = [];
      } else {
        queryParams.categoryType = [...allCategoryTypeValues];
      }
    }
  }
);

// 负责人相关逻辑
const ownerListRaw = ref<any[]>([]);
const ownerOptions = computed(() => {
  // 下拉值取 name 字段
  return ownerListRaw.value.map((o) => ({ label: o.name, value: o.name }));
});
const allOwnerValues = computed(() => ownerOptions.value.map((it) => it.value));
const isAllOwners = computed(() => {
  const selected = queryParams.owner;
  const all = allOwnerValues.value;
  return all.length > 0 && selected.length === all.length;
});
const isIndeterminateOwners = computed(() => {
  const len = queryParams.owner.length;
  return len > 0 && len < allOwnerValues.value.length;
});
watch(
  () => queryParams.owner,
  (newVal) => {
    if (newVal.includes("__ALL__")) {
      const realValues = newVal.filter((v) => v !== "__ALL__");
      if (realValues.length === allOwnerValues.value.length) {
        queryParams.owner = [];
      } else {
        queryParams.owner = [...allOwnerValues.value];
      }
    }
  }
);

const searchTypeOptions = [
  { label: "SKU", value: "sku" },
  { label: "MSKU", value: "seller_sku" },
  { label: "ASIN", value: "asin" },
  { label: "S-TAG", value: "tag" },
];

// 占位表格数据
const tableData = ref<any[]>([]);
const pageNum = ref(1);
const pageSize = ref(50);
const total = ref(0);

// 归类判断逻辑 (仅取后端 db_classification)
const getCategoryBySku = (row: any): string => {
  return row.db_classification || "";
};

// 价格格式化辅助函数
const formatPrice = (price: any, currency: string) => {
  if (price === undefined || price === null || price === "") return "";
  let symbol = currency;
  switch (currency) {
    case "EUR":
      symbol = "€";
      break;
    case "USD":
      symbol = "$";
      break;
    case "GBP":
      symbol = "£";
      break;
    case "JPY":
    case "CNY":
      symbol = "¥";
      break;
    case "CAD":
      symbol = "C$";
      break;
    case "AUD":
      symbol = "A$";
      break;
  }
  return symbol ? `${symbol} ${price}` : `${price}`;
};

const CACHE_KEY_QUERY = "SALES_LISTING_QUERY_PARAMS_V2";

function saveQueryToCache() {
  const cacheData = {
    queryParams,
    pageNum: pageNum.value,
    pageSize: pageSize.value,
  };
  localStorage.setItem(CACHE_KEY_QUERY, JSON.stringify(cacheData));
}

function loadQueryFromCache() {
  const cached = localStorage.getItem(CACHE_KEY_QUERY);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      // 恢复 queryParams
      if (parsed.queryParams) {
        Object.assign(queryParams, parsed.queryParams);
      }
      // 恢复分页信息
      if (parsed.pageNum) pageNum.value = parsed.pageNum;
      if (parsed.pageSize) pageSize.value = parsed.pageSize;
    } catch (e) {
      console.error("加载查询缓存失败", e);
    }
  }
}

function handleFilterChange() {
  pageNum.value = 1;
  handleQuery();
}

function handleQuery() {
  loading.value = true;
  saveQueryToCache(); // 保存缓存
  const params = {
    pageNum: pageNum.value,
    pageSize: pageSize.value,
    ...queryParams,
  };

  SalesProductListingAPI.getPage(params)
    .then((res: any) => {
      // 假设响应结构为 { total: number, data: ListingItemVO[] } 或符合 request 拦截器处理后的结构
      const list = res.data || [];
      tableData.value = list.map((item: ListingItemVO) => {
        // 查找店铺名称 (兼容 id 为数字或字符串的情况)
        const shopObj = shopListRaw.value.find((s) => String(s.id) === String(item.sid));
        const shopName = shopObj ? shopObj.label || shopObj.name : item.sid;

        // 状态转义：转为数字判定，避免 "1.0" 等带点字符串导致匹配失败或由前端自行截断
        const statusVal = Number(item.status);
        const isDeleteVal = Number(item.is_delete);
        const currency = (item as any).currency_code;

        // 处理大类排名分类：优先取 seller_category (可能是字符串化的列表)，否则取 seller_category_new (列表)
        const rankCatRaw = item.seller_category || (item as any).seller_category_new;
        let rankCat = "";

        if (Array.isArray(rankCatRaw)) {
          rankCat = rankCatRaw.join("； ");
        } else if (typeof rankCatRaw === "string") {
          const str = rankCatRaw.trim();
          if (str.startsWith("[") && str.endsWith("]")) {
            try {
              // 1. 尝试标准 JSON 解析
              const parsed = JSON.parse(str);
              if (Array.isArray(parsed)) rankCat = parsed.join("； ");
              else rankCat = String(parsed);
            } catch {
              // 2. 如果标准解析失败（例如 Python 风格单引号 ['A','B']），尝试手动处理
              // 去除首尾括号
              const content = str.slice(1, -1);
              if (!content.trim()) {
                rankCat = "";
              } else {
                // 简单按逗号分割，并去除每一项的首尾引号
                rankCat = content
                  .split(",")
                  .map((s) => s.trim().replace(/^['"]|['"]$/g, ""))
                  .join("； ");
              }
            }
          } else {
            // 普通字符串直接使用
            rankCat = str;
          }
        }

        return {
          // 保留原始字段供后续操作使用
          seller_sku: item.seller_sku,
          local_sku: item.local_sku,
          db_classification: item.db_classification,

          image: item.small_image_url,
          msku: item.seller_sku,
          fnsku: item.fnsku,
          // 品名/SKU
          skuName: item.local_name
            ? item.local_sku
              ? `${item.local_name}/${item.local_sku}`
              : item.local_name
            : item.local_sku || "-",
          shop: shopName,
          country: item.marketplace,
          // 状态转义 1: on, 0: off (处理可能的小数点问题)
          status:
            isDeleteVal === 1
              ? "deleted"
              : statusVal === 1
                ? "on"
                : statusVal === 0
                  ? "off"
                  : "unknown",
          createTime: item.open_date_display, // 使用 open_date_display
          asin: item.asin,
          parentAsin: item.parent_asin,
          title: item.item_name,
          // Classification -> Computed from MSKU or SKU
          classification: getCategoryBySku(item),
          // tag -> global_tags
          solarTermTag: "",
          price: formatPrice(item.price, currency),
          totalPrice: formatPrice(item.landed_price, currency),
          discountPrice: formatPrice(item.listing_price, currency),
          category: "", // item.seller_category  不取数据
          fbaSellable: item.afn_fulfillable_quantity,
          estFbaFee: formatPrice((item as any).shipping, currency),
          referralFee: "",
          salesToday: "", // 接口未提供今日销量
          salesYesterday: item.yesterday_volume,
          sales7_14_30: `${item.total_volume || 0} | ${item.fourteen_volume || 0} | ${item.thirty_volume || 0}`,
          rank: {
            rank: item.seller_rank,
            category: rankCat,
          },
          profit: "", // 需计算或接口补充
          salesTrend: "",
          avgSales7_14_30: `${item.average_seven_volume || 0} | ${item.average_fourteen_volume || 0} | ${item.average_thirty_volume || 0}`,
          salesAmountYesterday: formatPrice(item.yesterday_amount, currency),
          salesAmount7_14_30: `${formatPrice(item.seven_amount || 0, currency)} | ${formatPrice(item.fourteen_amount || 0, currency)} | ${formatPrice(item.thirty_amount || 0, currency)}`,
          adCostYesterday: "",
          adCost7_14_30: "",
          smallRank: (item as any).small_rank || [],
          rating: {
            value: Number(item.last_star || 0),
            count: item.review_num || 0,
          },
          owner: item.principal_info
            ? item.principal_info.map((p) => p.principal_name).join(", ")
            : "",
          openTime: item.on_sale_time,
          firstOrderTime: item.first_order_time,
          remarks: "",
          pairType: "", // 需后端提供

          // 隐藏列数据映射
          fulfillment: item.fulfillment_channel_type,
          brand: item.seller_brand,
          productCode: "",
          variants: "",
          localBrand: "",
          b2bPrice: "",
          listPrice: "",
          fbmStock: item.quantity,
        };
      });
      total.value = res.total || 0;

      // 获取节气标签
      const asins = tableData.value.map((item) => item.asin).filter(Boolean) as string[];
      if (asins.length > 0) {
        SolarTermTagAPI.queryByAsins(asins).then((data: any) => {
          // Response list: [{asin: "...", tags: [...]}, ...]
          const map: Record<string, string[]> = {};
          if (Array.isArray(data)) {
            data.forEach((t: any) => {
              if (t.asin) map[t.asin] = t.tags || [];
            });
          }
          asinTagsMap.value = map;
        });
      } else {
        asinTagsMap.value = {};
      }
    })
    .finally(() => {
      loading.value = false;
    });
}

function handleResetQuery() {
  queryFormRef.value?.resetFields?.();
  // 确保多选字段重置为数组
  queryParams.country = [];
  queryParams.shopId = [];
  queryParams.listingStatus = [];
  queryParams.pairStatus = [];
  queryParams.categoryType = [];
  queryParams.owner = [];
  queryParams.searchType = "sku";
  queryParams.keywords = "";
  queryParams.reportUpdatedAt = undefined;
  // 排序也会被清除，如果需要保留，请注释下面两行
  queryParams.sort = undefined;
  queryParams.order = undefined;
  // 清除搜索类型及关键字
  queryParams.searchType = "sku";
  queryParams.keywords = "";

  // 清除 Element Table 的排序状态 (通过 ref 调用 table 的 clearSort)
  // 此处因 el-table 未绑定 ref，可暂略，或给 table 加 ref="tableRef"
  handleQuery();
}

/**
 * 排序处理
 * { prop, order }: { prop: string, order: 'ascending' | 'descending' | null }
 */
function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  queryParams.sort = prop;
  queryParams.order = order;
  // 当 order 为 null 时，表示取消排序，恢复默认
  handleQuery();
}

onMounted(async () => {
  // 1. 先加载本地缓存的查询条件
  loadQueryFromCache();

  // 2. 获取店铺下拉数据 (await 确保店铺字典加载完毕后再请求列表，解决店铺名无法匹配的问题)
  try {
    const res = await ShopsAPI.getOptions();
    shopListRaw.value = res || [];
  } catch (err) {
    console.error("加载店铺数据失败", err);
  }

  // 加载负责人数据
  try {
    const res = await ShopsAPI.getOwners();
    ownerListRaw.value = res || [];
  } catch (err) {
    console.error("加载负责人数据失败", err);
  }

  // 3. 执行查询
  handleQuery();
});

function handleSizeChange(size: number) {
  pageSize.value = size;
  pageNum.value = 1;
  handleQuery();
}
function handleCurrentChange(page: number) {
  pageNum.value = page;
  handleQuery();
}
</script>

<style scoped>
/* 布局优化：确保表格区域自适应高度，滚动条在表格内部 */
.app-container {
  display: flex;
  flex-direction: column;
  height: 100%; /* 需配合父级容器高度 */
  padding-bottom: 0px; /* 减小整页底部留白 */
  overflow: hidden;
}
.data-table {
  display: flex;
  flex: 1;
  flex-direction: column;
  margin-top: -4px; /* 减小与搜索栏的间距 */
  overflow: hidden;
}
:deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  /* 减小内边距，特别是顶部，以压缩设置栏上方空间 */
  padding: 8px 10px 8px 10px;
}
.data-table__content {
  flex: 1;
  height: 0; /* 关键属性：强制 flex 子项高度收缩 */
}

/* 搜索栏整体字体稍小 */
.search-container {
  --el-font-size-base: 13px;
  padding-top: 12px; /* 上边距加宽 */
  padding-bottom: 2px; /* 下边距 */
}
/* 控制搜索项横向间距为 20px，且大幅减小底部间距以节省高度 */
.search-container :deep(.el-form--inline .el-form-item) {
  margin-right: 20px;
  margin-bottom: 10px; /* 下边距收窄 */
  margin-left: 10px;
}
/* 搜索行内部的按钮与输入框保持一点间距 */
.search-container :deep(.search-row .ml-2) {
  margin-left: 8px;
}
/* 单独将“店铺”这一项的 label 字体调小 */
.search-container :deep(.label-xs .el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
}
/* 所有搜索项的 label 字体统一为 12px 加粗 */
.search-container :deep(.el-form-item__label) {
  font-size: 12px;
  font-weight: 600;
}
/* 表头样式：居中、12px、加粗、黑体、黑色 */
:deep(.el-table__header th) {
  text-align: center;
}
:deep(.el-table__header th .cell) {
  display: block;
  width: 100%;
  font-family: SimHei, "Microsoft YaHei", sans-serif; /* 黑体 */
  font-size: 12px;
  font-weight: 600;
  color: #000; /* 表头黑色 */
  /* 强制表头文字居中，避免非固定列仍为左对齐 */
  text-align: center;
}

/* 表格内容字体小一号，颜色深一点但比表头浅 */
:deep(.el-table .el-table__cell) {
  padding: 4px 0 !important;
  font-size: 12px;
  color: #333; /* 内容深灰色 */
}

/* 文本容器：用于 MSKU, SKU Name 等 */
.cell-text-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%; /* 确保容器能限制宽度 */
  line-height: 1.4;
}
/* 单行文本溢出隐藏 */
.text-ellipsis {
  display: block;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 图片容器 36x36，居中 */
.thumb-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin: 0 auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}
/* 图片大小 34x34 */
.thumb-img {
  display: block;
  width: 34px;
  height: 34px;
}
/* 表格行高 48px */
:deep(.el-table__row) {
  height: 48px;
}
</style>

<style>
/* 下拉框全选选项吸顶样式 (需在非 scoped 中定义以作用于 teleported 的 popper) */
.select-all-option {
  position: sticky !important;
  top: 0 !important;
  z-index: 10 !important;
  background-color: var(--el-bg-color-overlay) !important;
  border-bottom: 1px solid var(--el-border-color-light);
}

/* 店铺下拉搜索框 去除边框和阴影 (覆盖所有状态) */
.shop-filter-input .el-input__wrapper,
.shop-filter-input .el-input__wrapper:hover,
.shop-filter-input .el-input__wrapper.is-focus {
  padding-left: 0;
  box-shadow: none !important;
}
</style>
