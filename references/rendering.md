# 渲染与尺寸：在 GitHub 上量出来的数

写作和验收都要用到几个固定数字。这一页只放实测结果，不放建议——建议在 [结构、版式与编辑示范](patterns.md)。

测得条件：2026-11-01，Chrome 156 headless，用 CDP 的 `Emulation.setDeviceMetricsOverride` 设定视口，样本是一个公开仓库的 README 页面（一个 macOS 磁盘占用分析工具，当天版本），取 `article.markdown-body` 的 `getBoundingClientRect()`。这个数只取决于 GitHub 的页面结构，换成别的仓库结果相同；复现方法见文末，可以自己换一个仓库再跑一遍。

## 正文列宽固定 838px

| 视口 | 正文列宽 | 左边距 |
| --- | --- | --- |
| 1280 × 900 | 838 | 65 |
| 1440 × 900 | 838 | 145 |
| 1920 × 1080 | 838 | 385 |
| 390 × 844 | 324 | 33 |

桌面端不管窗口多宽，正文列都是 838px，变的是左右留白。所以验收按 838 算，不要按「视口宽 × 某个比例」算。

另有一份同类文档建议按 900px 验收，比实测宽 62px——按 900 算会把 7.4% 的缩放量漏掉，一张 1200 单位宽的图正好差这么多。

## 字号换算

图按 100% 铺满正文列时：

```text
渲染字号 = 图内声明的字号 × 838 ÷ 图的 viewBox 宽
```

1200 单位宽的图，16 单位的标签渲染成 `16 × 838 ÷ 1200 ≈ 11.2px`。要让它不低于 12px，标签至少要 18 单位。视口再宽也不会变大，因为列宽不涨。

12px 是经验下限，不是平台规定：本仓库没有做过不同字号的可读性实验，只做到「低于它时，中文在 1x 屏上明显吃力」。引用这条时按经验值对待。

## 图片宽度的实际行为

| 写法 | 实测渲染宽 | 说明 |
| --- | --- | --- |
| `<img width="838">` | 838 | 与声明一致 |
| 不写 `width` | 838 | 被容器限到列宽 |
| `<img src="*.gif">` | 838 | GitHub 会给 GIF 套一层包装，`getAttribute('width')` 读不到原值，但宽度仍按容器限制 |
| 表格单元格里的 `<img width="410">` | 392.3 | 单元格 419.3px，减去左右内边距合计约 27px，内容区只剩 392.3px，`max-width: 100%` 把它压了下来 |

最后一行是并排图的坑：两张 410 的图不是占 820px，而是各占 392.3px，比例被压掉 4.3%；如果靠「410 + 410 = 820 < 838」来算刚好塞得下，实际每张图都比预期小一圈，字号跟着一起缩。并排两张时按每张不超过 392px 算。

## 自己复核

在目标页面上打开 DevTools，选中正文元素，在 Console 里跑：

```js
const a = document.querySelector('article.markdown-body') || document.querySelector('.markdown-body');
console.log('正文列', a.getBoundingClientRect().width);
[...a.querySelectorAll('img')]
  .filter(i => i.getBoundingClientRect().width > 300)
  .forEach(i => console.log(
    i.currentSrc.split('/').pop(),
    '渲染', Math.round(i.getBoundingClientRect().width),
    '原图', i.naturalWidth + '×' + i.naturalHeight,
    'width 属性', i.getAttribute('width')
  ));
```

改过 README 的图之后重跑一次，不要凭印象判断「看起来变大了」。

量不到时如实写「未在真实渲染下量过」，不要把估算值写成实测值。
