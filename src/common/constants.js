export const DEBUG = false
export const SETTINGS_KEY = "settings"
export const SAVE_KEY = "user_save_data"
export const AUTO_SAVE_KEY = "auto_save_data"
export const CLEARS_KEY = "starry_clears"

// 后日谈章节：本作（《星空列车与白的旅行》）为单线结局，无后日谈
export const AFTER_STORIES = []

// 使用.json格式的文本似乎在实体机上读取不到剧本（就算模拟器读的到），故此处使用txt存储
// 场景列表由内容包 src/common/game.txt 驱动（引擎 data-driven），不再在此维护。
// 场景分块：chunk001.txt … chunk017.txt（《星空列车与白的旅行》17 章剧本）

// 剧本节点类型
export const SCN_TYPE = {
  LABEL: 0, // 标签/跳转点 [0, "label_name"]
  CHAPTER_TITLE: 1, // 章节标题 [1, "章节标题"]
  BACKGROUND: 2, // 背景切换 [2, "bg_name"]
  DIALOGUE: 3, // 对话 [3, "说话人", "内容", [立绘列表]] // 立绘列表可空
  SELECT: 4, // 选项 [4, [["文字", "跳转", "表达式"]]]
  EV: 5, // 事件CG [5, "ev_img_name"]
  NEXT: 6 // 跳转至（下一章？） [6, "target_label"]
}
