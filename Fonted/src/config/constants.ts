/**
 * 与后端 app/config.py 保持一致的枚举常量
 * 修改时请同步更新后端对应配置
 */

/** 食材类别 — 对应后端 INGREDIENT_CATEGORIES */
export const INGREDIENT_CATEGORIES = [
  "肉", "蛋", "蔬菜", "水果", "奶制品", "谷物", "豆类", "坚果", "海鲜", "其他"
] as const

/** 菜系列表 — 对应后端 CUISINES */
export const CUISINES = [
  "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
  "东北菜", "西北菜", "家常菜", "西餐", "日料", "韩餐", "东南亚菜", "其他"
] as const

/** 烹饪方式 — 对应后端 METHODS */
export const METHODS = [
  "蒸", "煮", "炸", "炒", "焖", "拌", "卤", "烤", "煎", "腌", "炖", "其他"
] as const
