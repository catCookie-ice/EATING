/**
 * 食谱工具函数
 */

/** 根据食谱名称返回对应的 emoji */
export function getRecipeEmoji(name: string): string {
  const emojiMap: Record<string, string> = {
    '炒': '🍳', '煮': '🍲', '蒸': '🥟', '炸': '🍟', '烤': '🍕',
    '焖': '🍚', '凉拌': '🥗', '沙拉': '🥗', '汤': '🍜', '面': '🍜',
    '饭': '🍚', '肉': '🥩', '鱼': '🐟', '鸡': '🍗', '蔬': '🥬', '默认': '🍽️'
  }
  for (const key in emojiMap) {
    if (name.includes(key)) return emojiMap[key]
  }
  return emojiMap['默认']
}

/** 获取食谱的第一张图片 */
export function getFirstImage(recipe: any): string | null {
  if (recipe.pictures_url && Array.isArray(recipe.pictures_url) && recipe.pictures_url.length > 0) {
    return recipe.pictures_url[0]
  }
  return null
}
