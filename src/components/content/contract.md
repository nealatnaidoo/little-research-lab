## COMPONENT_ID
C1-content

## PURPOSE
Manage content lifecycle (posts, pages, resources) with state machine transitions.
Handles create, update, publish, archive operations with proper status transitions.

## INPUTS
- `CreateContentInput`: Create new content (type, title, slug, body)
- `UpdateContentInput`: Update existing content fields
- `PublishContentInput`: Transition content to published state
- `ArchiveContentInput`: Archive content
- `GetContentInput`: Retrieve content by ID or slug
- `ListContentInput`: List content with filters

## OUTPUTS
- `ContentOutput`: Single content item with metadata
- `ContentListOutput`: List of content items with pagination
- `ContentOperationOutput`: Operation result with errors if any

## DEPENDENCIES (PORTS)
- `ContentRepoPort`: Database access for content persistence
- `RulesPort`: Content rules (types, status machine, publish guards)
- `TimePort`: Time source for timestamps

## SIDE EFFECTS
- Database write on create/update/publish/archive
- Status transition validation via rules

## INVARIANTS
- I1: Content slug is unique per type
- I2: Status transitions follow state machine (draft -> scheduled/published)
- I3: Published content cannot be deleted (must archive first)
- I4: Content type must be in allowed types list
- I5: Publish guards must pass before publish

## ERROR SEMANTICS
- Returns errors in output object for validation failures
- Throws for database/infrastructure errors
- Idempotent operations where possible

## TESTS
- `tests/unit/test_content.py`: TA-0009 through TA-0013 (46 tests)
  - Content CRUD operations
  - Status transition validation
  - Slug uniqueness enforcement

## EVIDENCE
- `artifacts/pytest-content-report.json`
