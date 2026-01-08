# Changelog

## [2.2.0-dev] - 2026-01-08
### Added
- Implemented comprehensive event logging system with `events` and `user_event_logs` tables to track user activities and security events.
- Added unified audit utility (`log_and_notify`) for centralized logging and email notification across authentication flows.
- Introduced permission-based access control (RBAC) with support for roles and permissions for both users and API keys.
- Added structured API response models for better Swagger/OpenAPI documentation, including request and response schemas for all auth endpoints.
- Implemented 2FA (TOTP) support with temporary JWT tokens for enhanced account security.

### Changed
- Refactored authentication system: rewrote registration, login, logout, and account activation flows with improved security and error handling.
- Migrated from sync Redis to async Redis for session management while maintaining sync Redis for RQ job queuing.
- Updated database models to include TOTP secret fields and extended user event tracking capabilities.
- Improved error response consistency across all endpoints with unified `ErrorResponse` model.

### Fixed
- Resolved slowapi compatibility issues by ensuring all endpoints return proper Response objects.
- Fixed cookie handling for 2FA flows to properly distinguish between auth cookies and temporary 2FA cookies.


## [2.2.0-dev] - 2025-11-29
### Added
- Enhanced the login system to improve security and user experience.
- Updated email templates for account-related notifications, including activation, password reset, and login alerts.

### Changed
- Refactored the authentication module to streamline the login process and integrate additional security measures.


## [2.2.0-dev] - 2025-11-27
### Changed
- Refactored the entire codebase and switched to the `refactor/2.2.0` branch for development.
- Migrated database operations from `pymysql` to `SQLAlchemy`.
- Replaced the application server from `uvicorn` to `gunicorn`.
- Improved the implementation of the Rate Limiter.
- etc.

### Notes
- Version 2.1.0 was not released, skipped directly to 2.2.0-dev.


## [2.0.1-dev] - 2025-05-14
### Added
- Integrated *Logto as a new authentication method, providing users with more secure and flexible login options.
- Implemented background task processing to handle long-running operations asynchronously, improving application responsiveness.

### Changed
- Updated the random image feature to utilize a new API endpoint, ensuring continued access to random images.

### Other Changes
- Numerous minor improvements, code refactoring, and bug fixes have been implemented throughout the application to enhance stability and performance.


## [2.0.0-dev] - 2025-03-09
### Changed
- Code Refactoring: Rewrote all backend code to improve maintainability, performance, and scalability.
- Logging System: Refactored logging mechanism to provide better debugging capabilities and structured logging format.
- Database Handling: Optimized database queries and transactions to enhance efficiency and consistency.
- API Structure: Restructured API endpoints for better organization and modularity.
- Security Enhancements: Improved authentication, authorization, and input validation mechanisms to mitigate security risks.
- Configuration Management: Centralized and improved configuration handling to support different environments more effectively.
- Error Handling: Standardized error handling across the application for better debugging and monitoring.
- Performance Optimization: Reduced redundant computations and improved caching strategies to enhance overall performance.


## [1.0.0] - 2024-12-28
- Initial release.


# CoolAPI

This is the refactored version of the CoolAPI project, where we have restructured the UI and added new features.

## Archived Project

For the archived version of the CoolAPI project, please visit [CoolAPI-Old](https://github.com/redbean0721/CoolAPI-archive).

> Note: This is the previous version of the project, and it is no longer actively maintained.
