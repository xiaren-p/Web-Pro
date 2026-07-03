/**
 * 广告活动详情页业务逻辑 composable。
 *
 * @module useCampaignDetail
 * @description 封装活动信息加载、竞价调整（关键词/定位组/商品投放）、状态调整。
 *              视图层负责路由解析、子面板引用和 Tab 切换。
 */

import { ref, type Ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getAdCampaignDetail,
  type AdCampaignDetailResponse,
  adjustKeywordBid,
  adjustKeywordState,
  adjustTargetBid,
  adjustTargetState,
  adjustProductTargetBid,
  adjustProductTargetState,
} from "@/api/ads";

export function useCampaignDetail(campaignId: Ref<string>, profileId: Ref<string>) {
  /** 广告活动基础信息。 */
  const campaignInfo = ref<AdCampaignDetailResponse | null>(null);

  /**
   * 加载广告活动详情。
   */
  function loadCampaignInfo(): void {
    getAdCampaignDetail(campaignId.value, profileId.value)
      .then((res) => {
        campaignInfo.value = res;
      })
      .catch(() => {
        // 加载失败时保持展示 campaign_id 作为展示名称
      });
  }

  /**
   * 将投放类型格式化为中文。
   *
   * @param val - targeting_type 原始值（AUTO / MANUAL）。
   * @returns 中文显示文字。
   */
  function formatTargetingType(val: string): string {
    if (!val) return "";
    const map: Record<string, string> = { AUTO: "自动", MANUAL: "手动" };
    return map[val.toUpperCase()] ?? val;
  }

  /**
   * 关键词竞价修改：写调整记录 + 更新行数据 bid。
   */
  async function onKeywordBid({ row, bid }: { row: any; bid: number }): Promise<void> {
    if (!row?.keyword_id) {
      ElMessage.error("缺少关键词标识，无法修改竞价");
      return;
    }
    const oldBid = row.bid;
    try {
      await adjustKeywordBid({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        keyword_id: row.keyword_id,
        bid_after: bid,
      });
      row.bid = bid;
      row._bidInput = bid;
      ElMessage.success("竞价修改已记录，待执行推送");
    } catch (error) {
      row.bid = oldBid;
      row._bidInput = oldBid;
      console.error("[onKeywordBid] 修改竞价失败", error);
      ElMessage.error("修改竞价失败");
    }
  }

  /**
   * 关键词状态修改。
   */
  async function onKeywordState({
    row,
    state,
  }: {
    row: any;
    state: "enabled" | "paused";
  }): Promise<void> {
    if (!row?.keyword_id) {
      ElMessage.error("缺少关键词标识，无法修改状态");
      return;
    }
    const oldState = row.state;
    try {
      await adjustKeywordState({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        keyword_id: row.keyword_id,
        state,
      });
      row.state = state;
      ElMessage.success(state === "enabled" ? "启用已记录，待执行推送" : "暂停已记录，待执行推送");
    } catch (error) {
      row.state = oldState;
      console.error("[onKeywordState] 修改状态失败", error);
      ElMessage.error("修改状态失败");
    }
  }

  /**
   * 自动定位组竞价修改。
   */
  async function onTargetBid({ row, bid }: { row: any; bid: number }): Promise<void> {
    if (!row?.target_id) {
      ElMessage.error("缺少定位组标识，无法修改竞价");
      return;
    }
    const oldBid = row.bid;
    try {
      await adjustTargetBid({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        target_id: row.target_id,
        bid_after: bid,
      });
      row.bid = bid;
      row._bidInput = bid;
      ElMessage.success("竞价修改已记录，待执行推送");
    } catch (error) {
      row.bid = oldBid;
      row._bidInput = oldBid;
      console.error("[onTargetBid] 修改竞价失败", error);
      ElMessage.error("修改竞价失败");
    }
  }

  /**
   * 自动定位组状态修改。
   */
  async function onTargetState({
    row,
    state,
  }: {
    row: any;
    state: "enabled" | "paused";
  }): Promise<void> {
    if (!row?.target_id) {
      ElMessage.error("缺少定位组标识，无法修改状态");
      return;
    }
    const oldState = row.state;
    try {
      await adjustTargetState({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        target_id: row.target_id,
        state,
      });
      row.state = state;
      ElMessage.success(state === "enabled" ? "启用已记录，待执行推送" : "暂停已记录，待执行推送");
    } catch (error) {
      row.state = oldState;
      console.error("[onTargetState] 修改状态失败", error);
      ElMessage.error("修改状态失败");
    }
  }

  /**
   * 商品投放竞价修改。
   */
  async function onProductTargetBid({ row, bid }: { row: any; bid: number }): Promise<void> {
    if (!row?.target_id || !row?.campaign_id || !row?.profile_id) {
      ElMessage.error("缺少商品投放标识，无法修改竞价");
      return;
    }
    const oldBid = row.bid;
    try {
      await adjustProductTargetBid({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        target_id: row.target_id,
        bid_after: bid,
      });
      row.bid = bid;
      row._bidInput = bid;
      ElMessage.success("竞价修改已记录，待执行推送");
    } catch (error) {
      row.bid = oldBid;
      row._bidInput = oldBid;
      console.error("[onProductTargetBid] 修改竞价失败", error);
      ElMessage.error("修改竞价失败");
    }
  }

  /**
   * 商品投放状态修改。
   */
  async function onProductTargetState({
    row,
    state,
  }: {
    row: any;
    state: "enabled" | "paused";
  }): Promise<void> {
    if (!row?.target_id || !row?.campaign_id || !row?.profile_id) {
      ElMessage.error("缺少商品投放标识，无法修改状态");
      return;
    }
    const oldState = row.state;
    try {
      await adjustProductTargetState({
        campaign_id: campaignId.value,
        profile_id: profileId.value,
        target_id: row.target_id,
        state,
      });
      row.state = state;
      ElMessage.success(state === "enabled" ? "启用已记录，待执行推送" : "暂停已记录，待执行推送");
    } catch (error) {
      row.state = oldState;
      console.error("[onProductTargetState] 修改状态失败", error);
      ElMessage.error("修改状态失败");
    }
  }

  return {
    campaignInfo,
    loadCampaignInfo,
    formatTargetingType,
    onKeywordBid,
    onKeywordState,
    onTargetBid,
    onTargetState,
    onProductTargetBid,
    onProductTargetState,
  };
}
