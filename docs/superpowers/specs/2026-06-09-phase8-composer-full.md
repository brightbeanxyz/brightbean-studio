# Phase 8: Composer + Calendar Full Port

## Goal

Port the Django composer and calendar apps to Kotlin. This phase replaces the simplistic
placeholder Post/PlatformPost/PostStatus models with the full 10-state editorial workflow,
adds all composer models (ContentCategory, Tag, IdeaGroup, Idea, IdeaMedia, PostMedia,
PostVersion, PostTemplate, CSVImportJob, Feed), and all calendar models (PostingSlot,
Queue, QueueEntry, RecurrenceRule, CustomCalendarEvent).

## Current State (Gap Analysis)

### Domain models that need REPLACING/ENHANCING

| Model | Current state | Required changes |
|-------|--------------|-----------------|
| `PostStatus` | 6-value enum (DRAFT, SCHEDULED, PENDING_APPROVAL, PUBLISHED, FAILED, CANCELLED) | Replace with 10-value `PlatformPostStatus` enum matching Django's PlatformPost.Status |
| `Post` | Simple data class with `content: String`, `platforms: List<PlatformType>`, inline `status: PostStatus` | Enhance: add `title`, `caption`, `firstComment`, `internalNotes`, `tags` as JSON, remove `platforms` list (replaced by PlatformPost children), remove `status` field (derived from children), keep `scheduledAt`, `publishedAt`, `mediaIds` |
| `PlatformPost` | Simple data class with minimal fields | Full enhancement: add `PlatformPostStatus` state machine with `canTransitionTo()`/`transitionTo()`, platform-specific overrides (`platformCaption`, `platformTitle`, `platformFirstComment`, `platformMedia` JSON, `platformExtra` JSON), `scheduledAt`, `retryCount`, `nextRetryAt`, `publishError` |
| `ContentCategory` | Exists but missing `position` | Add `position: Int`, `updatedAt: Instant` |
| `Tag` | Exists, adequate | No changes needed |
| `Idea` | Minimal stub (title + content only) | Full rebuild: add `description`, `tags` (JSON), `status` (IdeaStatus enum), `groupId`, `position`, `postId`, `mediaAssetId` |

### Domain models that need CREATING (new)

| Model | Source table | Key fields |
|-------|-------------|-----------|
| `IdeaGroup` | `composer_idea_group` | workspaceId, name, position |
| `IdeaMedia` | `composer_idea_media` | ideaId, mediaAssetId, position |
| `PostMedia` | `composer_post_media` | postId, mediaAssetId, position, altText, platformOverrides (JSON) |
| `PostVersion` | `composer_post_version` | postId, versionNumber, snapshot (JSON), createdBy |
| `PostTemplate` | `composer_post_template` | workspaceId, name, description, templateData (JSON), createdBy |
| `CSVImportJob` | `composer_csv_import_job` | workspaceId, uploadedBy, fileName, columnMapping (JSON), status, totalRows, processedRows, resultSummary (JSON) |
| `Feed` | `composer_feed` | workspaceId, name, url, websiteUrl, addedBy |
| `PostingSlot` | `calendar_posting_slot` | socialAccountId, dayOfWeek (0-6), time (LocalTime), isActive |
| `Queue` | `calendar_queue` | workspaceId, name, categoryId?, socialAccountId, isActive |
| `QueueEntry` | `calendar_queue_entry` | queueId, postId, position, assignedSlotDatetime |
| `RecurrenceRule` | `calendar_recurrence_rule` | postId (1:1), frequency (daily/weekly/monthly), interval, endDate, lastGeneratedAt, isActive |
| `CustomCalendarEvent` | `calendar_custom_event` | workspaceId, title, description, startDate, endDate, color, createdBy |

### Domain repositories that need CREATING

| Repository | Key methods |
|-----------|------------|
| `ContentCategoryRepository` | findById, findByWorkspaceId, save, update, delete |
| `TagRepository` | findById, findByWorkspaceId, findByName, save, delete |
| `IdeaRepository` | findById, findByWorkspaceId, findByGroupId, findByAuthorId, save, update, delete |
| `IdeaGroupRepository` | findById, findByWorkspaceId, save, update, delete |
| `IdeaMediaRepository` | findByIdeaId, save, deleteByIdeaId |
| `PostMediaRepository` | findByPostId, save, deleteByPostId, delete |
| `PostVersionRepository` | findByPostId, findLatestByPostId, save |
| `PostTemplateRepository` | findById, findByWorkspaceId, save, update, delete |
| `CSVImportJobRepository` | findById, findByWorkspaceId, save, update |
| `FeedRepository` | findById, findByWorkspaceId, save, delete |
| `PostingSlotRepository` | findById, findBySocialAccountId, findActiveBySocialAccountId, save, update, delete |
| `QueueRepository` | findById, findByWorkspaceId, save, update, delete |
| `QueueEntryRepository` | findByQueueId, save, delete, updatePosition |
| `RecurrenceRuleRepository` | findByPostId, findActive, save, update, delete |
| `CustomCalendarEventRepository` | findById, findByWorkspaceId, findByDateRange, save, update, delete |

### Use cases that need REWRITING

| Use case | Current | Required changes |
|----------|---------|-----------------|
| `CreatePostUseCase` | Creates Post with inline status | Rewrite: create Post (no status field) + N PlatformPosts (one per social account, status=DRAFT), PostMedia rows |
| `PublishPostUseCase` | Publishes to all platforms at once | Rewrite: publish individual PlatformPost via state machine transition, use new provider signatures |
| `SchedulePostUseCase` | Simple schedule | Rewrite: transition PlatformPosts to SCHEDULED, set scheduled_at per-platform, sync parent |
| `ApprovePostUseCase` | Simple approval | Rewrite: transition PlatformPost to APPROVED via state machine |

### Use cases that need CREATING

| Use case | Purpose |
|----------|---------|
| `TransitionPlatformPostUseCase` | Transition a single PlatformPost through the state machine with validation |
| `SyncPostScheduledAtUseCase` | Set Post.scheduledAt to earliest PlatformPost.scheduled_at |
| `SavePostVersionUseCase` | Create immutable PostVersion snapshot |
| `ContentCategoryUseCases` | CRUD for categories (create, update, delete, list) |
| `IdeaUseCases` | Create, edit, delete, move, convert-to-post |
| `IdeaGroupUseCases` | Create, delete, reorder |
| `PostTemplateUseCases` | Save-as-template, list, delete, use-template |
| `PostingSlotUseCases` | CRUD for posting slots |
| `QueueUseCases` | Create queue, add-to-queue, reorder, assign-slots |
| `CustomCalendarEventUseCases` | CRUD for calendar events |
| `ReschedulePostUseCase` | Drag-and-drop reschedule for calendar |

### Flyway V5 migration needed

Drop old `post` table (V1), `platform_post` table (V2), `publishing_queue` table (V2).
Create all composer and calendar tables matching Django schema.
(The old tables were scaffold placeholders, not production data.)

## Sub-Phase Breakdown

### P8A: Enhanced Domain Models + Flyway V5

1. Replace `PostStatus` with `PlatformPostStatus` (10-state enum)
2. Add `derivePostStatus()` pure function (port of Django's `status.py`)
3. Enhance `Post` model (add title, caption, firstComment, internalNotes, remove platforms/status)
4. Enhance `PlatformPost` model (full state machine, platform overrides, scheduling fields)
5. Enhance `ContentCategory` model (add position, updatedAt)
6. Create `IdeaGroup`, `IdeaMedia` models
7. Enhance `Idea` model (add all fields)
8. Create `PostMedia`, `PostVersion`, `PostTemplate`, `CSVImportJob`, `Feed` models
9. Create `PostingSlot`, `Queue`, `QueueEntry`, `RecurrenceRule`, `CustomCalendarEvent` models
10. Create all new repository interfaces
11. Flyway V5: drop old tables, create new tables matching Django schema
12. Update all existing DAOs and JDBI repos for new model shapes
13. Create all new DAOs and JDBI repos

### P8B: Composer Use Cases

1. Rewrite `CreatePostUseCase` (Post + N PlatformPosts + PostMedia)
2. Rewrite `PublishPostUseCase` (per-PlatformPost state machine)
3. Rewrite `SchedulePostUseCase` (transition PlatformPosts)
4. Rewrite `ApprovePostUseCase` (state machine transition)
5. Create `TransitionPlatformPostUseCase`
6. Create `SyncPostScheduledAtUseCase`
7. Create `SavePostVersionUseCase`
8. Create `ContentCategoryUseCases`
9. Create `IdeaUseCases` (create, edit, delete, move, convert-to-post)
10. Create `IdeaGroupUseCases` (create, delete, reorder)

### P8C: Calendar Use Cases + Templates + Feeds

1. Create `PostingSlotUseCases`
2. Create `QueueUseCases` (create, add-to-queue, reorder, assign-slots, delete)
3. Create `CustomCalendarEventUseCases`
4. Create `ReschedulePostUseCase`
5. Create `PostTemplateUseCases`
6. Create `FeedUseCases` (add, delete, list)

### P8D: API Endpoints + Tests

1. Create `ComposerApi` handler (create/save/autosave/delete post)
2. Create `PlatformPostApi` handler (transition, list)
3. Create `CategoryApi` handler (CRUD)
4. Create `IdeaApi` handler (CRUD + move + convert)
5. Create `IdeaGroupApi` handler (CRUD + reorder)
6. Create `TemplateApi` handler (CRUD)
7. Create `CalendarApi` handler (view, reschedule, posting slots, queues, events)
8. Update `ApiDispatcher` with new routes
9. Update `RBACMiddleware` for new route patterns
10. Update `ApplicationModule` with all new use cases
11. Update `InfrastructureModule` with all new repos
12. Fix all existing tests for new model shapes
13. Write new tests for all use cases and API handlers

## State Machine (PlatformPostStatus)

```
DRAFT → {PENDING_REVIEW, SCHEDULED, PUBLISHING}
PENDING_REVIEW → {APPROVED, CHANGES_REQUESTED, REJECTED}
APPROVED → {PENDING_CLIENT, SCHEDULED, PUBLISHING, DRAFT}
PENDING_CLIENT → {APPROVED, CHANGES_REQUESTED, REJECTED}
CHANGES_REQUESTED → {PENDING_REVIEW, DRAFT}
REJECTED → {DRAFT, PENDING_REVIEW}
SCHEDULED → {PUBLISHING, DRAFT}
PUBLISHING → {PUBLISHED, FAILED, SCHEDULED}  // SCHEDULED = retry
FAILED → {PUBLISHING, DRAFT, SCHEDULED}
PUBLISHED → {}  // terminal
```

## Django-to-Kotlin Naming Conventions

| Django | Kotlin |
|--------|--------|
| `composer_content_category` | `composer_content_category` (same) |
| `composer_tag` | `composer_tag` (same) |
| `composer_idea_group` | `composer_idea_group` (same) |
| `composer_idea` | `composer_idea` (same) |
| `composer_idea_media` | `composer_idea_media` (same) |
| `composer_post` | `composer_post` (replaces `post`) |
| `composer_platform_post` | `composer_platform_post` (replaces `platform_post`) |
| `composer_post_media` | `composer_post_media` (new) |
| `composer_post_version` | `composer_post_version` (new) |
| `composer_post_template` | `composer_post_template` (new) |
| `composer_csv_import_job` | `composer_csv_import_job` (new) |
| `composer_feed` | `composer_feed` (new) |
| `calendar_posting_slot` | `calendar_posting_slot` (new) |
| `calendar_queue` | `calendar_queue` (new) |
| `calendar_queue_entry` | `calendar_queue_entry` (new) |
| `calendar_recurrence_rule` | `calendar_recurrence_rule` (new) |
| `calendar_custom_event` | `calendar_custom_event` (new) |

## Key Implementation Notes

1. **Post.status is DERIVED** — not stored in DB. The `derivePostStatus(platformPostStatuses)` pure function
   aggregates child PlatformPost statuses. The `post` table has NO status column.

2. **PlatformPost owns editorial state** — each social account flows through the workflow independently.

3. **State machine is enforced in domain model** — `PlatformPost.transitionTo(newStatus)` throws on invalid
   transitions. The use case layer catches and returns error.

4. **Flyway V5 is destructive** — it drops the old `post`, `platform_post`, `publishing_queue` tables
   and recreates them with the full Django schema. This is safe because the Kotlin port has no production data.

5. **Platform-specific overrides** use nullable fields on PlatformPost (`platformCaption: String?`)
   where null means "fall back to parent Post value".

6. **JSON fields** (tags, platform_media, platform_extra, template_data, etc.) stored as TEXT/JSONB
   with Jackson serialization in DAOs.

7. **Queue slot assignment** algorithm: walk forward day-by-day up to 60 days, match active PostingSlots
   by weekday, assign sequential entries to sequential slots.

8. **No HTML rendering** — the Kotlin port only exposes JSON APIs. All Django template/HTMX logic
   becomes JSON response bodies.
