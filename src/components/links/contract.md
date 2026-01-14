# Links Component Contract

## COMPONENT_ID
`links`

## PURPOSE
Manages navigation and social links for the link hub page. Provides CRUD operations for links with validation, duplicate slug detection, and ordering support.

## INPUTS

### CreateLinkInput
- `title: str` - Display title for the link (required, max 200 chars)
- `slug: str` - URL-friendly identifier (required, max 100 chars, unique)
- `url: str` - Target URL (required, must start with http:// or https://)
- `icon: str | None` - Optional icon identifier
- `status: LinkStatus` - "active" or "inactive" (default: "active")
- `position: int` - Sort order position (default: 0)
- `visibility: ContentVisibility` - "public" or "private" (default: "public")
- `group_id: UUID | None` - Optional group for organizing links

### UpdateLinkInput
- `link_id: UUID` - ID of link to update (required)
- All other fields optional - only provided fields are updated

### DeleteLinkInput
- `link_id: UUID` - ID of link to delete

### GetLinkInput
- `link_id: UUID` - ID of link to retrieve

## OUTPUTS

### LinkOperationOutput
- `link: LinkItem | None` - The resulting link (None on error)
- `errors: tuple[LinkValidationError, ...]` - Validation errors if any
- `success: bool` - Whether the operation succeeded

### LinkListOutput
- `links: tuple[LinkItem, ...]` - All links
- `total: int` - Count of links

## DEPENDENCIES (PORTS)

### LinkRepoPort
```python
class LinkRepoPort(Protocol):
    def save(self, link: LinkItem) -> LinkItem: ...
    def get_all(self) -> list[LinkItem]: ...
    def get_by_id(self, link_id: UUID) -> LinkItem | None: ...
    def delete(self, link_id: UUID) -> None: ...
```

## SIDE EFFECTS
- `run_create`: Persists new link via `LinkRepoPort.save()`
- `run_update`: Updates existing link via `LinkRepoPort.save()`
- `run_delete`: Removes link via `LinkRepoPort.delete()`
- `run_get`, `run_list`: Read-only operations

## INVARIANTS
1. **Unique slugs**: No two links may have the same slug
2. **Valid URLs**: All URLs must start with `http://` or `https://`
3. **Title length**: Titles must be ≤200 characters
4. **Slug length**: Slugs must be ≤100 characters
5. **Required fields**: title, slug, url are required for creation

## ERROR SEMANTICS

### Validation Errors (LinkValidationError)
| Code | Message | Field |
|------|---------|-------|
| `title_required` | Title is required | title |
| `title_too_long` | Title must be 200 characters or less | title |
| `slug_required` | Slug is required | slug |
| `slug_too_long` | Slug must be 100 characters or less | slug |
| `slug_duplicate` | Link with slug '{slug}' already exists | slug |
| `url_required` | URL is required | url |
| `url_invalid_scheme` | URL must start with http:// or https:// | url |
| `link_not_found` | Link with ID {id} not found | - |

## TESTS
- `test_create_link_success` - Creates link with valid data
- `test_create_link_duplicate_slug` - Rejects duplicate slug
- `test_create_link_invalid_url` - Rejects invalid URL scheme
- `test_update_link_success` - Updates existing link
- `test_update_link_not_found` - Returns error for missing link
- `test_delete_link_success` - Deletes existing link
- `test_delete_link_not_found` - Returns error for missing link
- `test_list_links` - Returns all links with count
- `test_get_link_by_id` - Returns link by ID

## EVIDENCE
- Unit tests in `tests/unit/test_links.py`
- Integration with SQLiteLinkRepo in adapter tests
