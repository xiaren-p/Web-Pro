/**
 * 商品图片上传管理 API：分页、表单、批量同步、CSV 导入。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 图片上传分页查询参数。 */
export interface ImageUploadPageQuery extends PageQuery {
  imageGroup?: string;
  status?: string;
}

/** 图片上传记录 VO。 */
export interface ImageUploadVO {
  id: string;
  imageGroup?: string;
  status?: string;
  cloudPath?: string;
  log?: string;
  imageUrl?: string;
  createTime?: string;
  /** 失败店铺ID列表：null=从未同步，空串=全部成功，逗号分隔=部分失败 */
  failedShops?: string | null;
}

/** 图片上传表单。 */
export interface ImageUploadForm {
  id?: string;
  imageGroup?: string;
  cloudPath?: string;
  status?: string;
  log?: string;
  imageUrl?: string;
}

/** 图片同步队列查询参数。 */
export interface ImageSyncQueueQuery extends PageQuery {
  imageGroup?: string;
}

/** 图片同步队列返回对象。 */
export interface ImageSyncQueueVO {
  id: string;
  imageGroup: string;
  cloudPath: string;
  status: string;
  errorMsg: string;
  createTime: string;
}

const IMAGE_UPLOAD_BASE_URL = "/image-uploads";

export const ImageUploadAPI = {
  /**
   * 分页查询图片上传记录。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: ImageUploadPageQuery) {
    return request<any, PageResult<ImageUploadVO[]>>({ url: `${IMAGE_UPLOAD_BASE_URL}/page`, method: "get", params });
  },
  /**
   * 获取图片上传编辑表单数据。
   *
   * @param id - 记录ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, ImageUploadForm>({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建图片上传记录。
   *
   * @param data - 表单数据。
   */
  create(data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新图片上传记录。
   *
   * @param id - 记录ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除图片上传记录。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${ids}`, method: "delete" });
  },
  /**
   * 同步单个图片组。
   *
   * @param id - 记录ID。
   * @param forceResync - true=强制重新同步，false=断点同步（仅未成功项）。
   */
  sync(id: string, forceResync: boolean = false) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}/sync`, method: "post", data: { forceResync } });
  },
  /**
   * 批量同步图片组。
   *
   * @param ids - ID列表。
   * @param forceResync - true=强制重新同步，false=断点同步。
   */
  batchSync(ids: string[], forceResync: boolean = false) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/batch_sync`, method: "post", data: { ids, forceResync } });
  },
  /**
   * 分页查询同步队列。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getQueue(params: ImageSyncQueueQuery) {
    return request<any, PageResult<ImageSyncQueueVO[]>>({ url: `${IMAGE_UPLOAD_BASE_URL}/queue`, method: "get", params });
  },
  /**
   * 导入 CSV 文件。
   *
   * @param file - CSV 文件。
   */
  importCsv(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/import_csv`, method: "post", data: formData, headers: { "Content-Type": "multipart/form-data" } });
  },
  /**
   * 批量创建图片上传记录。
   *
   * @param data - 记录数组。
   */
  batchCreate(data: ImageUploadForm[]) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/batch`, method: "post", data });
  },
};
