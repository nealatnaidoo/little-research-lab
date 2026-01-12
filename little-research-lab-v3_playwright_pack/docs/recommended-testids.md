# Recommended `data-testid` list

These IDs keep Playwright tests stable and minimize brittle locators.

## /admin/login
- `login-email`
- `login-password`
- `login-submit`
- `nav-dashboard` (or dashboard heading `admin-dashboard-title`)

## /admin (dashboard)
- `admin-dashboard-title`

## /admin/settings
- `settings-site-title`
- `settings-site-description`
- `settings-og-image-asset-picker`
- `settings-save`
- `toast-success` (or `settings-save-success`)

## /admin/assets
- `assets-upload-input`
- `assets-upload-submit` (if separate)
- `assets-table`
- `asset-row-{asset_id}` (optional)
- `asset-set-latest-{asset_id}` (optional)

## /admin/redirects
- `redirects-from`
- `redirects-to`
- `redirects-create`
- `redirects-table`
- `redirect-row-{from}` (optional)
- `redirect-delete-{from}` (optional)
- `redirect-error` (for validation messages)

## /admin/audit
- `audit-table`
- `audit-row` (repeated)
- `audit-filter` (optional)

## /admin/content (posts/resources)
- `content-create`
- `content-title`
- `content-slug`
- `content-status`
- `content-save`
- `content-publish-now`
- `content-schedule`
- `content-cancel-schedule`

## /admin/analytics
- `analytics-kpi-views`
- `analytics-kpi-downloads`
- `analytics-chart-views`
- `analytics-table-top-content`
> Ensure no PII columns/fields are ever shown.

