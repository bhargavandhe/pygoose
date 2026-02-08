# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-08

### Added

- **Core ODM Features:**
  - Async-first MongoDB object-document mapper (ODM) with PyMongo async client
  - Document base class with CRUD operations (create, read, update, delete)
  - QuerySet fluent query builder with lazy evaluation
  - Type-safe document references with Ref[T] generic type
  - Reference population engine with depth limits (MAX_POPULATE_DEPTH = 5)
  - Dirty field tracking for efficient updates
  - Collection auto-naming with naive pluralization

- **Field Types:**
  - PyObjectId custom type for BSON ObjectId fields
  - Encrypted[T] field-level encryption using Fernet
  - Indexed[T] field with index specifications
  - Support for all Pydantic v2 field types

- **Lifecycle Hooks:**
  - Pre/post validation hooks (pre_validate)
  - Pre/post save hooks (pre_save, post_save)
  - Pre/post delete hooks (pre_delete, post_delete)
  - Post update hooks (post_update)

- **Encryption System:**
  - EncryptionManager for managing encryption keys
  - Field-level encryption with Fernet symmetric encryption
  - Safe key rotation with progress tracking
  - Automatic decryption on document load
  - Optional encrypted fields support

- **Plugin System:**
  - TimestampsMixin: Automatic created_at/updated_at tracking
  - SoftDeleteMixin: Soft delete support with is_deleted flag
  - AuditMixin: ContextVar-based audit trail tracking with per-request context

- **FastAPI Integration:**
  - init_app() for seamless FastAPI setup
  - Custom exception handlers for Pygoose exceptions
  - Automatic schema generation for documents
  - Pagination parameter helpers

- **Utilities:**
  - Pagination models (Page, CursorPage)
  - Custom exceptions (DocumentNotFound, MultipleDocumentsFound, etc.)
  - Query event monitoring and observability
  - Filter merging utilities

- **Documentation:**
  - Comprehensive getting started guide
  - Core concepts documentation
  - Advanced features documentation
  - Complete API reference
  - FastAPI integration guide
  - Real-world examples

### Changed

- Reorganized codebase into logical directories:
  - `pygoose/core/` - Core ODM infrastructure
  - `pygoose/fields/` - Field types and metadata
  - `pygoose/lifecycle/` - Hooks and observability
  - `pygoose/plugins/` - Reusable mixins
  - `pygoose/integrations/` - Framework integrations
  - `pygoose/utils/` - Utilities and helpers

- **Breaking Changes (intentional for v0.1.0):**
  - Changed encryption API from `set_encryption_key()` to `encryption.set_key()`
  - Changed encryption API from `get_encryption_key()` to `encryption.get_key()`
  - Removed `_reset_encryption()` wrapper in favor of `encryption.reset()`
  - Removed `_pluralize()` from public API (now internal in utils)

- Enhanced Document.update() with Pydantic validation before DB writes
- Improved populate depth validation with MAX_POPULATE_DEPTH (5 levels)
- Added comprehensive logging for encryption, connection, and query operations
- Improved error messages with context and validation details

### Fixed

- Connection error handling with URI and database name validation
- Populate query circular reference protection
- Encrypted field detection using Pydantic's `__pydantic_init_subclass__`
- Settings resolution with SettingsResolver utility class
- Code duplication in filter merging (created merge_filters() utility)

### Dependencies

- pymongo >= 4.8 (async client)
- pydantic >= 2.4 (v2 models)
- cryptography >= 42.0 (optional, for encryption)
- fastapi >= 0.100 (optional, for FastAPI integration)

### Testing

- 149 comprehensive tests covering all features
- AsyncIO test support with pytest-asyncio
- Tests for core CRUD, queries, references, encryption, hooks, plugins, and integrations

---

## Future Versions

### [0.2.0] (Planned)
- Connection pooling configuration
- Bulk operations (insertMany, updateMany, deleteMany)
- Aggregation pipeline support
- Full-text search support
- Change stream support for real-time updates
- Additional plugin types (versioning, etc.)

### [0.3.0] (Planned)
- Performance optimizations
- Index management utilities
- Query optimization helpers
- Database schema migration tools
- Additional framework integrations (Starlette, Quart, etc.)
