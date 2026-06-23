/**
 * 商品图片上传管理 API：分页、表单、批量同步、CSV 导入。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface ImageUploadPageQuery extends PageQuery {
  imageGroup?: string;
  status?: string;
}

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
  getPage(params: ImageUploadPageQuery) {
    return request<any, PageResult<ImageUploadVO[]>>({
      url: `${IMAGE_UPLOAD_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, ImageUploadForm>({
      url: `${IMAGE_UPLOAD_BASE_URL}/${id}/form`,
      method: "get",
    });
  },
  create(data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${ids}`, method: "delete" });
  },
  /** 同步单个图片组。forceResync=true 强制重新同步，false=断点同步（仅未成功项）。 */
  sync(id: string, forceResync: boolean = false) {
    return request({
      url: `${IMAGE_UPLOAD_BASE_URL}/${id}/sync`,
      method: "post",
      data: { forceResync },
    });
  },
  /** 批量同步。forceResync=true 强制重新同步，false=断点同步。 */
  batchSync(ids: string[], forceResync: boolean = false) {
    return request({
      url: `${IMAGE_UPLOAD_BASE_URL}/batch_sync`,
      method: "post",
      data: { ids, forceResync },
    });
  },
  getQueue(params: ImageSyncQueueQuery) {
    return request<any, PageResult<ImageSyncQueueVO[]>>({
      url: `${IMAGE_UPLOAD_BASE_URL}/queue`,
      method: "get",
      params,
    });
  },
  importCsv(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request({
      url: `${IMAGE_UPLOAD_BASE_URL}/import_csv`,
      method: "post",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  batchCreate(data: ImageUploadForm[]) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/batch`, method: "post", data });
  },
};
