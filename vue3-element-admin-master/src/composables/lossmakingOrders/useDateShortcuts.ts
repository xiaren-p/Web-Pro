/**
 * 日期范围选择器快捷选项工厂：今天 / 昨天 / 最近 7 / 30 天 / 本月 / 上月 / 今年 / 去年。
 * 所属板块：statistics / lossmakingOrders（如其他页面需要可下沉到 composables/common/）。
 *
 * 设计：通过传入 setRange 闭包注入页面端的 v-model 写入器，避免本文件直接耦合视图状态。
 */

/** 日期范围设置器签名。 */
export type DateRangeSetter = (range: [Date, Date]) => void;

/** 单个快捷项的结构（兼容 ElDatePicker shortcuts）。 */
export interface DateShortcut {
  text: string;
  onClick: (picker: any) => void;
}

/**
 * 尝试通过 picker 内部方法立即确认/关闭面板。
 * Element Plus 不同版本暴露的方法名不一，逐一尝试以兼容。
 */
export function emitPickerPick(
  picker: any,
  start: Date,
  end: Date,
  setRange: DateRangeSetter
): void {
  try {
    if (!picker) return;
    setRange([start, end]);

    const tryCall = (obj: any, name: string): boolean => {
      try {
        if (!obj) return false;
        const fn = obj[name];
        if (typeof fn === "function") {
          fn.call(obj);
          return true;
        }
      } catch {
        /* ignore */
      }
      return false;
    };

    const methodCandidates = [
      "confirm",
      "handleConfirm",
      "doConfirm",
      "onConfirm",
      "hidePicker",
      "close",
      "closePicker",
      "togglePicker",
    ];

    for (const m of methodCandidates) {
      if (tryCall(picker, m)) return;
      if (picker.proxy && tryCall(picker.proxy, m)) return;
      if (picker.component && tryCall(picker.component, m)) return;
    }

    if (typeof picker.emit === "function") {
      try {
        picker.emit("pick", [start, end]);
      } catch {
        /* ignore */
      }
      try {
        picker.emit("confirm");
      } catch {
        /* ignore */
      }
    }
  } catch {
    /* swallow */
  }
}

/**
 * 创建一组标准日期快捷项，setRange 用于回写到调用方的响应式状态。
 */
export function createDateShortcuts(setRange: DateRangeSetter): DateShortcut[] {
  return [
    {
      text: "今天",
      onClick: (picker: any) => {
        const end = new Date();
        const start = new Date();
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "昨天",
      onClick: (picker: any) => {
        const d = new Date();
        d.setDate(d.getDate() - 1);
        emitPickerPick(picker, d, d, setRange);
        setRange([d, d]);
      },
    },
    {
      text: "最近7天",
      onClick: (picker: any) => {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - 6);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "最近30天",
      onClick: (picker: any) => {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - 29);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "本月",
      onClick: (picker: any) => {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "上月",
      onClick: (picker: any) => {
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const end = new Date(now.getFullYear(), now.getMonth(), 0);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "今年",
      onClick: (picker: any) => {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 1);
        const end = new Date(now.getFullYear(), 11, 31);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
    {
      text: "去年",
      onClick: (picker: any) => {
        const now = new Date();
        const start = new Date(now.getFullYear() - 1, 0, 1);
        const end = new Date(now.getFullYear() - 1, 11, 31);
        emitPickerPick(picker, start, end, setRange);
        setRange([start, end]);
      },
    },
  ];
}
