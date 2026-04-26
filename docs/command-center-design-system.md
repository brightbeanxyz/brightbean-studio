# Social Command Center Design System

Design system này dùng cho toàn bộ giao diện Social Command Center theo hướng luxury dark SaaS: tối, sâu, rõ dữ liệu, có chất liệu glass-metal và micro-interaction vừa phải.

## Token Namespace

Tất cả token mới dùng prefix `--scc-*` trong `theme/static_src/src/styles.css`. Các biến cũ như `--obsidian-*`, `--champagne`, `--surface-*`, `--text-*`, `--shadow-*`, `--radius-*`, `--dur-*` đã được map lại để không phá các màn hiện có.

## Colors

Core surfaces:

- `--scc-bg-primary`: `#0B0D12`
- `--scc-bg-secondary`: `#11141B`
- `--scc-surface-card`: `#151A22`
- `--scc-surface-elevated`: `#1B222D`
- `--scc-surface-raised`: `#222B38`
- `--scc-border-subtle`: `rgba(255, 255, 255, 0.08)`
- `--scc-border-strong`: `rgba(255, 255, 255, 0.16)`

Text:

- `--scc-text-primary`: nội dung chính
- `--scc-text-heading-color`: heading và số liệu lớn
- `--scc-text-secondary`: mô tả, metadata quan trọng
- `--scc-text-muted`: metadata phụ
- `--scc-text-faint`: label, hint, divider text

Accents:

- `--scc-accent-gold`: champagne, dùng cho primary action và key highlight
- `--scc-accent-blue`: insight/info/data highlight
- `--scc-accent-emerald`: positive growth/success
- `--scc-accent-violet`: AI/advanced analytics accent

Status:

- `--scc-danger`, `--scc-warning`, `--scc-success`, `--scc-info`
- Mỗi status có bản `*-soft` để làm nền chip/card nhẹ.

Platform:

- `--scc-platform-facebook`
- `--scc-platform-tiktok`
- `--scc-platform-youtube`

## Typography

- `--scc-font-display`, `--scc-font-body`, `--scc-font-mono`
- `--scc-text-display`: hero title, page headline
- `--scc-text-heading-size`: dashboard heading
- `--scc-text-section`: section title trong card
- `--scc-text-label`: uppercase label
- `--scc-text-body`: body text
- `--scc-text-caption`: caption/metadata
- `--scc-leading-display`, `--scc-leading-heading`, `--scc-leading-body`, `--scc-leading-dense`

Metric nên dùng class `.scc-u-metric` để bật tabular numbers.

## Radius

- `--scc-radius-sm`: `4px`
- `--scc-radius-md`: `6px`
- `--scc-radius-lg`: `8px`
- `--scc-radius-xl`: `12px`
- `--scc-radius-2xl`: `16px`
- `--scc-radius-full`: pill/chip

Card analytics chính nên ưu tiên `--scc-radius-lg` để giữ cảm giác sắc, cao cấp.

## Shadow And Depth

- `--scc-shadow-inset-soft`: highlight mép trên
- `--scc-shadow-card`: card glass-metal mặc định
- `--scc-shadow-card-elevated`: drawer, sticky panel, modal
- `--scc-shadow-hover`: hover elevation
- `--scc-glow-gold`, `--scc-glow-blue`, `--scc-glow-emerald`, `--scc-glow-violet`: glow tinh tế theo accent

Không dùng shadow quá sáng hoặc neon lớn; ưu tiên depth nền tối và border glow nhẹ.

## Spacing

Scale chính:

- `--scc-space-4`
- `--scc-space-8`
- `--scc-space-12`
- `--scc-space-16`
- `--scc-space-20`
- `--scc-space-24`
- `--scc-space-32`
- `--scc-space-40`

Dashboard mật độ cao nên dùng gap `12px` hoặc `16px`; hero/major sections dùng `20px` hoặc `24px`.

## Motion

- `--scc-motion-120`: focus, small chip, subtle state
- `--scc-motion-180`: filter, button, hover cơ bản
- `--scc-motion-240`: card lift, tab panel
- `--scc-motion-320`: drawer, modal, larger layout transition

Easing:

- `--scc-ease-hover`
- `--scc-ease-drawer`
- `--scc-ease-tabs`
- `--scc-ease-filter`

## Utility Classes

Surface:

- `.scc-u-surface`
- `.scc-u-surface-elevated`
- `.scc-u-hairline-top`
- `.scc-u-hover-lift`
- `.scc-u-focus-ring`

Typography:

- `.scc-u-display`
- `.scc-u-heading`
- `.scc-u-section-title`
- `.scc-u-label`
- `.scc-u-body`
- `.scc-u-caption`
- `.scc-u-metric`

Color text:

- `.scc-u-text-primary`
- `.scc-u-text-secondary`
- `.scc-u-text-muted`
- `.scc-u-text-faint`
- `.scc-u-text-gold`
- `.scc-u-text-blue`
- `.scc-u-text-emerald`
- `.scc-u-text-violet`

Controls:

- `.scc-u-chip`
- `.scc-u-button`
- `.scc-u-button-primary`

Platform/status chips:

- `.scc-u-platform-facebook`
- `.scc-u-platform-tiktok`
- `.scc-u-platform-youtube`
- `.scc-u-status-success`
- `.scc-u-status-warning`
- `.scc-u-status-danger`
- `.scc-u-status-info`

Spacing helpers:

- `.scc-u-stack-4`
- `.scc-u-stack-8`
- `.scc-u-stack-12`
- `.scc-u-stack-16`
- `.scc-u-stack-20`
- `.scc-u-stack-24`
- `.scc-u-stack-32`
- `.scc-u-stack-40`

Scrollbar:

- `.scc-u-scrollbar`

## Example

```html
<section class="scc-u-surface scc-u-hairline-top scc-u-hover-lift">
  <p class="scc-u-label">Total reach</p>
  <strong class="scc-u-metric">12.8M</strong>
  <span class="scc-u-chip scc-u-status-success">+18.4%</span>
</section>
```
