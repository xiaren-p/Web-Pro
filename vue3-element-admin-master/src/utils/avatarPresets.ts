/**
 * 预设头像工具：基于 @dicebear/thumbs 风格，用固定种子在本地生成 12 个 SVG 头像。
 * 完全离线，不依赖外网，MIT 协议可商用。
 *
 * DB 存储格式：'preset:01' ~ 'preset:12'
 * 前端渲染：将标识符转为 SVG data URI，直接绑定到 <img :src="..."> 或 <el-avatar>
 */
import { createAvatar } from "@dicebear/core";
import * as thumbs from "@dicebear/thumbs";

/** 系统预设头像数量（与后端 PRESET_COUNT 保持一致） */
export const PRESET_COUNT = 12;

/** DB 存储前缀（与后端 PRESET_PREFIX 保持一致） */
export const PRESET_PREFIX = "preset:";

/**
 * 12 个固定种子，对应 preset:01 ~ preset:12。
 * 种子固定保证同一标识符在任何客户端渲染结果一致。
 */
const PRESET_SEEDS: Record<string, string> = {
  "preset:01": "lx-avatar-seed-alpha-001",
  "preset:02": "lx-avatar-seed-beta-002",
  "preset:03": "lx-avatar-seed-gamma-003",
  "preset:04": "lx-avatar-seed-delta-004",
  "preset:05": "lx-avatar-seed-epsilon-005",
  "preset:06": "lx-avatar-seed-zeta-006",
  "preset:07": "lx-avatar-seed-eta-007",
  "preset:08": "lx-avatar-seed-theta-008",
  "preset:09": "lx-avatar-seed-iota-009",
  "preset:10": "lx-avatar-seed-kappa-010",
  "preset:11": "lx-avatar-seed-lambda-011",
  "preset:12": "lx-avatar-seed-mu-012",
};

/** 缓存：避免重复生成同一 SVG */
const _svgCache = new Map<string, string>();

/**
 * 将预设标识符转换为 SVG data URI，可直接用于 <img src="..."> 或 <el-avatar :src="...">。
 *
 * @param {string} presetId - 预设标识符，格式 'preset:01' ~ 'preset:12'。
 * @returns {string} SVG data URI 字符串；若标识符无效则返回空字符串。
 *
 * @example
 * const src = presetToDataUri('preset:03')
 * // <el-avatar :src="src" />
 */
export function presetToDataUri(presetId: string): string {
  if (!isPreset(presetId)) return "";

  if (_svgCache.has(presetId)) {
    return _svgCache.get(presetId)!;
  }

  const seed = PRESET_SEEDS[presetId];
  if (!seed) return "";

  const avatar = createAvatar(thumbs, {
    seed,
    size: 256,
    backgroundColor: [
      "5c6bc0",
      "42a5f5",
      "26c6da",
      "66bb6a",
      "ffa726",
      "ef5350",
      "ab47bc",
      "26a69a",
      "8d6e63",
      "78909c",
      "ec407a",
      "7e57c2",
    ],
  });

  const dataUri = avatar.toDataUri();
  _svgCache.set(presetId, dataUri);
  return dataUri;
}

/**
 * 判断 avatar 字段值是否为系统预设头像标识符。
 *
 * @param {string} avatar - UserProfile.avatar 字段值。
 * @returns {boolean} True 表示预设头像，False 表示用户上传的 URL。
 */
export function isPreset(avatar: string): boolean {
  return Boolean(avatar) && avatar.startsWith(PRESET_PREFIX);
}

/**
 * 获取所有预设头像列表（用于选择器渲染）。
 *
 * @returns {Array<{ id: string; dataUri: string }>} 预设头像列表，按编号升序。
 */
export function getAllPresets(): Array<{ id: string; dataUri: string }> {
  return Array.from({ length: PRESET_COUNT }, (_, i) => {
    const id = `${PRESET_PREFIX}${String(i + 1).padStart(2, "0")}`;
    return { id, dataUri: presetToDataUri(id) };
  });
}

/**
 * 解析 avatar 字段，返回可直接用于 <el-avatar :src="..."> 的 URL 或 data URI。
 * - 若为预设标识符 → 转为 SVG data URI
 * - 若为普通 URL   → 原样返回
 * - 若为空         → 返回空字符串
 *
 * @param {string} avatar - UserProfile.avatar 字段值。
 * @returns {string} 可渲染的头像地址。
 */
export function resolveAvatarSrc(avatar: string): string {
  if (!avatar) return "";
  if (isPreset(avatar)) return presetToDataUri(avatar);
  return avatar;
}
