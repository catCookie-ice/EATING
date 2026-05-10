// 节日/特殊日期配置
// time 格式: MM-DD (月-日)
// content 支持链接格式: [显示文本](/recipes/ID) 或 [显示文本](/recipes?cuisine=菜系)

export interface HolidayConfig {
  time: string    // MM-DD 格式
  content: string // 支持 [文本](/path) 链接格式
}

export const holidayConfigs: HolidayConfig[] = [
  { time: '01-01', content: '新年伊始，来一顿[丰盛早餐](/recipes?cuisine=粤菜)开启美好一年！' },
  { time: '02-14', content: '今天是情人节，陈某对这天有些意见，所以，就这样吧' },
  { time: '05-01', content: '劳动节快乐！放假在家，来点[简易美食](/recipes?method=拌)' },
  { time: '05-10', content: '今天是母亲节，给母亲一个[特殊美食](/recipes/1)吧' },
  { time: '06-01', content: '儿童节到了！和孩子一起动手做[趣味料理](/recipes?cuisine=川菜)' },
  { time: '08-15', content: '中秋佳节，[月饼做法](/recipes/1)学起来！' },
  { time: '10-01', content: '国庆假期，来顿[庆祝大餐](/recipes?cuisine=湘菜)' },
  { time: '11-11', content: '双十一购物节，给自己买份[美食清单](/ingredients)' },
  { time: '12-25', content: '圣诞节🎄 [圣诞大餐](/recipes?cuisine=西餐)准备好了吗？' },
  { time: '02-05', content: '今日立春！试试[春饼](/recipes/1)迎接春天' },
  { time: '06-21', content: '今日夏至！清热解暑来碗[绿豆汤](/recipes/1)' },
  { time: '09-23', content: '今日秋分！润燥养肺试试[银耳莲子羹](/recipes/1)' },
  { time: '12-22', content: '今日冬至！[饺子](/recipes/1)安排上' },
]
