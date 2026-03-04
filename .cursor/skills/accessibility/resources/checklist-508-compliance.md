# Checklist: Section 508 Compliance

Pre-submission checklist for accessibility compliance.

---

## Keyboard Navigation

- [ ] All interactive elements accessible via keyboard (Tab, Enter, Space)
- [ ] Tab order is logical and follows visual order
- [ ] Focus indicators are visible on all focusable elements
- [ ] No keyboard traps (user can always navigate away)
- [ ] Modal dialogs trap focus and release on close
- [ ] Skip navigation link provided for repetitive content

---

## Screen Reader

- [ ] All images have appropriate `alt` text
- [ ] Decorative images have `alt=""`
- [ ] Form inputs have associated `<label>` elements
- [ ] ARIA labels used where semantic HTML insufficient
- [ ] Dynamic content changes announced via `aria-live`
- [ ] Page title is descriptive and unique
- [ ] Landmark roles present (`<main>`, `<nav>`, `<header>`)

---

## Color and Contrast

- [ ] Text contrast ratio is 4.5:1 minimum
- [ ] Large text contrast ratio is 3:1 minimum
- [ ] UI component contrast is 3:1 minimum
- [ ] Color is not the only means of conveying information
- [ ] Links are distinguishable from surrounding text

---

## Forms

- [ ] All inputs have visible labels
- [ ] Related inputs grouped with `<fieldset>` and `<legend>`
- [ ] Required fields marked visually and with `aria-required`
- [ ] Error messages are clear and associated with inputs
- [ ] Input format hints provided where needed
- [ ] Form validation feedback is accessible

---

## Structure and Navigation

- [ ] Headings follow logical hierarchy (h1 → h2 → h3)
- [ ] No heading levels skipped
- [ ] Lists use proper `<ul>`, `<ol>`, `<li>` markup
- [ ] Tables have proper headers and scope
- [ ] Navigation is consistent across pages
- [ ] Breadcrumbs provided for complex hierarchies

---

## Dynamic Content

- [ ] Focus managed when content updates
- [ ] Loading states announced to screen readers
- [ ] Errors announced to screen readers
- [ ] Custom controls follow ARIA authoring practices
- [ ] Route changes announce new page content

---

## Media

- [ ] Videos have captions
- [ ] Audio has transcripts
- [ ] Media players have accessible controls
- [ ] Autoplay is avoided or can be stopped
- [ ] No content flashes more than 3 times per second

---

## Target Size and Touch

- [ ] All interactive targets are at least 24x24 CSS pixels (WCAG 2.2 Level AA)
- [ ] Primary touch targets are at least 44x44 pixels (recommended)
- [ ] Adequate spacing between adjacent interactive elements
- [ ] Pinch-to-zoom is not disabled
- [ ] Content works in both portrait and landscape
- [ ] Tested with mobile screen readers

---

## Testing Tools

### Automated

- [ ] axe DevTools scan passed
- [ ] WAVE scan passed
- [ ] Lighthouse accessibility audit ≥90

### Manual

- [ ] Keyboard-only navigation tested
- [ ] Screen reader tested (NVDA, JAWS, or VoiceOver)
- [ ] Color contrast checked with DevTools
- [ ] Zoom to 200% tested
