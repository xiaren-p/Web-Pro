import { ref, reactive, computed, onMounted, nextTick, watch } from "vue";
import { ShopsAPI } from "@/api/shops";
import { SalesProductListingAPI, type ListingItemVO } from "@/api/sales/listing";
import {
  listingStatusOptions,
  pairStatusOptions,
  searchTypeOptions,
  categoryTypeOptions,
} from "./constants";

export function useListingTable() {
  const queryFormRef = ref();
  const loading = ref(false);

  const fallback = (val: any) => {
    return val === null || val === undefined || val === "" ? "--" : val;
  };

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
    // 下拉值取 name 字段或 uid
    return ownerListRaw.value.map((o) => ({
      label: o.name_zh || o.name,
      value: String(o.uid || o.id),
    }));
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

  // 占位表格数据
  const tableData = ref<any[]>([]);
  const pageNum = ref(1);
  const pageSize = ref(50);
  const total = ref(0);

  // 价格 / 金额 / 利润等格式化均由后端 serializer/view 完成（``*_display`` 字段），
  // 前端只负责取值与嵌代，不再作任何数据加工。

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
    nextTick(() => {
      pageNum.value = 1;
      handleQuery();
    });
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

          // 处理大类排名分类：优先取 seller_category (可能是字符串化的列表)，否则取 seller_category_new (列表)

          return {
            // 保留原始字段供后续操作使用
            seller_sku: item.seller_sku,
            local_sku: item.local_sku,
            assort: fallback((item as any).assort),
            db_classification: item.db_classification,

            id: (item as any).id || "--",
            listing_id: item.listing_id || (item as any).id,
            image: fallback(item.small_image_url),
            msku: fallback(item.seller_sku),
            fnsku: fallback(item.fnsku),
            // 品名/SKU
            skuName: item.local_name
              ? item.local_sku
                ? `${item.local_name}/${item.local_sku}`
                : item.local_name
              : item.local_sku || "--",
            shop: fallback(item.shop_name || shopName || item.sid),
            country: fallback(item.marketplace || item.country_code),
            // 状态转义 1: on, 0: off (处理可能的小数点问题)
            status:
              isDeleteVal === 1
                ? "deleted"
                : statusVal === 1
                  ? "on"
                  : statusVal === 0
                    ? "off"
                    : "unknown",
            open_date_time: fallback(item.open_date_display), // 使用 open_date_display 映射为 open_date_time 根据需要修改 mapping
            asin: fallback(item.asin),
            parentAsin: fallback(item.parent_asin),
            label: item.label || [],
            title: fallback(item.item_name),
            // Classification -> Computed from MSKU or SKU
            classification: "--",
            // tag -> global_tags
            solarTermTag: "--",
            price: fallback((item as any).price_display),
            totalPrice: fallback((item as any).landed_price_display),
            discountPrice: fallback((item as any).listing_price_display),
            fbaSellable: fallback(item.afn_fulfillable_quantity),
            estFbaFee: fallback((item as any).fba_fee_display),
            referralFee: fallback((item as any).referral_fee_display),
            salesToday: "--", // 接口未提供今日销量
            salesYesterday: fallback(item.yesterday_volume),
            sales7_14_30: `${fallback(item.total_volume)} | ${fallback(item.fourteen_volume)} | ${fallback(item.thirty_volume)}`,
            rank: {
              rank: fallback(item.seller_rank),
              category: fallback((item as any).small_category),
            },
            profit: {
              gross_margin: (item as any).profit_metrics?.gross_margin,
              gross_profit: (item as any).profit_metrics?.gross_profit,
              gross_margin_display: (item as any).gross_margin_display,
              gross_profit_display: (item as any).gross_profit_display,
            },
            avgSales7_14_30: `${fallback(item.average_seven_volume)} | ${fallback(item.average_fourteen_volume)} | ${fallback(item.average_thirty_volume)}`,
            salesAmountYesterday: fallback((item as any).yesterday_amount_display),
            salesAmount7_14_30: `${fallback((item as any).seven_amount_display)} | ${fallback((item as any).fourteen_amount_display)} | ${fallback((item as any).thirty_amount_display)}`,
            adCostYesterday: fallback((item as any).yesterday_spend_display),
            adCost7_14_30: `${fallback((item as any).seven_spend_display)} | ${fallback((item as any).fourteen_spend_display)} | ${fallback((item as any).thirty_spend_display)}`,
            smallRank: {
              rank: fallback((item as any).small_rank),
              category: fallback((item as any).small_category),
            },
            rating: {
              value: fallback(Number(item.last_star || 0)),
              count: fallback(item.review_num || 0),
            },
            owner: fallback(
              item.principal_info
                ? item.principal_info.map((p: any) => p.realname || p.principal_name).join(", ")
                : ""
            ),
            openTime: fallback(item.on_sale_time),
            firstOrderTime: fallback(item.first_order_time),
            remarks: fallback((item as any).remarks),
            // 隐藏列数据映射
            fulfillment: fallback(item.fulfillment_channel_type),
            brand: fallback(item.seller_brand),
            productCode: {
              id: fallback((item as any).amz_product_id),
              type: fallback((item as any).amz_product_id_type),
            },
            variants: fallback((item as any).variant_text),
            b2bPrice: fallback((item as any).b2b_price_display),
            listPrice: fallback((item as any).listing_price_display),
            fbmStock: fallback(item.afn_fulfillable_quantity),
          };
        });
        total.value = res.total || 0;
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

  return {
    queryFormRef,
    loading,
    fallback,
    queryParams,
    shopListRaw,
    countryOptions,
    allCountryValues,
    isAllCountries,
    isIndeterminateCountries,
    shopSearchKeyword,
    baseShopOptions,
    shopOptions,
    allShopValues,
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
    ownerListRaw,
    ownerOptions,
    allOwnerValues,
    isAllOwners,
    isIndeterminateOwners,
    searchTypeOptions,
    tableData,
    pageNum,
    pageSize,
    total,
    handleQuery,
    handleResetQuery,
    handleFilterChange,
    handleSortChange,
    handleSizeChange,
    handleCurrentChange,
  };
}
