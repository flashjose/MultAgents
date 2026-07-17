# HotHub 设计系统 — MASTER(全局唯一事实源)

> 风格定位:**Swiss Minimalism 纯黑白极简主义**
> 更新于 2026-07-17。
> 核心:纯黑白调色板、Inter 字体层级、数学网格、零装饰、黑白双主题切换。
> 布局:文字驱动排名列表(类微博热搜/知乎热榜)。

## 1. 设计哲学

- **Swiss Minimalism**:字体即设计。网格定义秩序。留白是元素。
- **纯黑白**：无彩色强调色。黑色 IS 强调色。层次靠灰阶区分。
- **双主题**：Light(白底黑字) / Dark(黑底白字)，跟随系统偏好，用户可手动切换。
- **零装饰**:无投影、无渐变、无圆角过度、无动画浮夸。只有网格、字体、线条。

## 2. 色彩令牌 — Light Theme (默认)

| 令牌 | 值 | 用途 |
|---|---|---|
| `--bg` | `#FAFAFA` | 页面底色 |
| `--card` | `#FFFFFF` | 条目/Header 表面 |
| `--ink` | `#09090B` | 主文本 |
| `--ink-soft` | `#3F3F46` | 次要文本 |
| `--ink-faint` | `#71717A` | 辅助信息 |
| `--border` | `#E4E4E7` | 默认边框 |
| `--border-hover` | `#A1A1AA` | 悬停边框 |
| `--muted` | `#E8ECF0` | 内嵌底 |
| `--accent` | `#18181B` | "强调"= 近黑(选中态、链接 hover) |
| `--accent-invert` | `#FAFAFA` | 强调位文字(白) |
| `--danger` | `#DC2626` | 错误态 |
| `--ring` | `#18181B` | 焦点环 |

## 3. 色彩令牌 — Dark Theme

| 令牌 | Dark 值 | 用途 |
|---|---|---|
| `--bg` | `#000000` | 纯黑底 |
| `--card` | `#0C0C0C` | 微提亮表面 |
| `--ink` | `#FAFAFA` | 主文本 |
| `--ink-soft` | `#A1A1AA` | 次要文本 |
| `--ink-faint` | `#71717A` | 辅助信息 |
| `--border` | `#3F3F46` | 默认边框 |
| `--border-hover` | `#52525B` | 悬停边框 |
| `--muted` | `#18181B` | 内嵌底 |
| `--accent` | `#FAFAFA` | "强调"= 近白 |
| `--accent-invert` | `#09090B` | 强调位文字(黑) |
| `--danger` | `#EF4444` | 错误态 |
| `--ring` | `#FAFAFA` | 焦点环 |

**规则:全站无彩色。层次完全由 `#000` → `#FFF` 之间的灰阶表达。**

## 4. 字体(Swiss 层级)

- **正文/UI**:`"Inter", "PingFang SC", "HarmonyOS Sans SC", "MiSans", "Microsoft YaHei", system-ui, sans-serif`
- **展示/品牌**:`"Playfair Display"`,仅用于 brand 名(斜体意大利风格点睛)
- **衬线点缀**:`"Noto Serif SC"`,仅用于 top-3 排名数字
- 字号层级:正文 14px、标题 15px/600、摘要 12px、热度 13px/600 tabular-nums、brand 24px/700 italic

## 5. 间距与圆角(Swiss 数学比例)

- 间距梯度:`8 / 12 / 16 / 24 / 32 / 48`
- 条目内边距:`12px 16px`
- 圆角:条目 `4px`(几乎直角,Swiss 锐利)、chips `4px`、缩略图 `4px`
- 容器 `max-width: 1200px`

## 6. 表面与效果 — 线条风格

- **零投影**:全站无 `box-shadow`
- **零动画浮夸**:无 `translateY`、无 scale、无 spring
- 悬停:仅 `background-color` 或 `border-color` 变化(150-200ms)
- 条目:1px `border-bottom` 分割,悬停加四边边框 + `--muted` 背景
- Chip:默认透明描边,选中 `--accent` 实底 + `--accent-invert` 字
- 缩略图:1px 边框,无阴影,`object-fit: cover`

## 7. 布局:文字驱动排名列表

- 单列垂直排列,`.gallery` 由 1px 边框包裹
- 每行:`[排名号 36×36] — [文字 flex:1] — [可选缩略图 90×68]`
- 排名号:top-3 用 `--accent` 实底 + Noto Serif SC
- 标题:2 行截断,15px/600,`--ink`
- 缩略图:右对齐固定尺寸,仅当 `cover_url` 存在时渲染
- 无图条目:文字占满宽度,无空白占位

## 8. 主题切换

- 默认跟随 `prefers-color-scheme`
- 手动切换写入 `localStorage("theme")` → `"light"` / `"dark"` / `"system"`
- `<html data-theme="dark">` 触发 Dark 变量覆盖
- 切换过渡:`transition: background-color 0.3s, color 0.3s` on `body`
- 图标:Sun/Moon SVG 描边图标

## 9. 反模式

- 任何彩色(包括橙色/蓝色/绿色强调)
- 任何投影
- 任何位移动画
- 圆角 > 6px
- 渐变背景
- 纹理噪点、玻璃拟态
- 无图条目留空占位
- 装饰性动画(>200ms)
