# Data Migration Layer

## Overview

This directory contains the infrastructure for migrating data from the Django SQLite database to the new Kotlin/JDBI PostgreSQL schema.

## Components

### MigrationRunner

`studio-infrastructure/src/main/kotlin/com/brightbean/studio/infrastructure/migration/MigrationRunner.kt`

A placeholder class that will orchestrate the migration process once Django database access is available.

## Migration Strategy

### Phase 1: Django Export
Connect to the Django `db.sqlite3` file via JDBC and export entities in topological order to avoid foreign key violations.

### Phase 2: Data Transform
- Map Django model fields to Kotlin data classes
- Remap IDs from Django auto-increment integers to UUIDs or JDBI-assigned IDs
- Validate data integrity

### Phase 3: PostgreSQL Import
- Use JDBI batch inserts for performance
- Transactional commits per entity type
- Idempotent operations (re-running skips already-migrated records)

## Entity Dependency Order

Due to foreign key constraints, migrations must execute in this order:

1. **Organizations** - no dependencies
2. **Members** - depends on Organization
3. **Workspaces** - depends on Organization
4. **SocialAccounts** - depends on Workspace, Member
5. **Credentials** - depends on SocialAccount
6. **Posts** - depends on Workspace, Member, Organization
7. **MediaItems** - depends on Post
8. **BlogPosts** - depends on Post
9. **StaticPages** - depends on Organization

## Known Limitations

- **Binary fields**: Profile images and other binary data require streaming to avoid out-of-memory errors
- **JSONField**: Django JSONField data must be validated for JSON structure compatibility with the Kotlin target
- **Timezone handling**: Django stores naive datetimes; migration must assume UTC
- **ManyToMany relationships**: Require join table migration after both related entities exist

## Running the Migration

```bash
java -cp app.jar com.brightbean.studio.infrastructure.migration.MigrationRunner \
  --source jdbc:sqlite:/path/to/db.sqlite3 \
  --target jdbc:postgresql://localhost:5432/studio \
  --types organization,member,workspace,socialaccount,post
```

## Status

This is a **placeholder implementation**. The actual migration runner requires access to the running Django database, which is not available during the initial porting phase. The placeholder throws `NotImplementedError` to prevent accidental use.
