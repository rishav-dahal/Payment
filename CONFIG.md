# Payment Microservice Configuration Guide

This guide explains how environment configuration is managed, details each configurable variable, and documents the production safety validation rules.

---

## Architecture Overview

Configurations are managed dynamically using **Pydantic Settings** (`pydantic-settings`). 
* Settings are declared with strict types inside [app/core/config.py](app/core/config.py).
* Values are automatically loaded from system environment variables or parsed from a local `.env` file.
* If a variable is missing, Pydantic falls back to its default value. If a variable contains an invalid type (e.g. string passed to an integer port), a validation error is thrown at startup.

---

## Configuration Reference

The following parameters are configured in the [.env](.env) file:

| Variable Name | Type / Format | Default | Description |
| :--- | :--- | :--- | :--- |
| **`ENVIRONMENT`** | `development` \| `testing` \| `staging` \| `production` | `development` | The deployment stage of the microservice. Influences log formats, debug modes, and safety checks. |
| **`PROJECT_NAME`** | `str` | `"Payment Service"` | Title metadata utilized in FastAPI application schemas and logging labels. |
| **`API_V1_STR`** | `str` | `"/api/v1"` | URL prefix prefixing all API endpoints. |
| **`DATABASE_URL`** | `str` | `sqlite:///./payment.db` | Connection string. Supports PostgreSQL and SQLite. (See *Auto-Normalization* below). |
| **`DB_POOL_SIZE`** | `int` | `5` | The connection pool limit kept open for PostgreSQL. (Ignored for SQLite). |
| **`DB_MAX_OVERFLOW`** | `int` | `10` | The limit of temporary overflow connections allowed for PostgreSQL. |
| **`SECRET_KEY`** | `str` | *Insecure placeholder* | Cryptographic secret for signing payloads. |
| **`API_KEY`** | `str` | *Insecure placeholder* | Secure token required for inter-service communication (header: `X-API-Key`). |
| **`BACKEND_CORS_ORIGINS`** | `JSON List` or `Comma-separated str` | `[]` | List of allowed browser origins. Supports JSON arrays like `["http://localhost:3000"]` or comma separation. |

---

## Custom Normalizations and Validations

To keep deployment robust, Pydantic processes the configuration using custom validators:

### 1. Database URL Auto-Normalization
* **Problem**: Cloud database hostings (e.g., Render, Heroku) frequently export database URLs starting with `postgres://`. However, SQLAlchemy version 1.4+ deprecated this in favor of `postgresql://` and crashes when detecting `postgres://`.
* **Fix**: The setting class intercepts any `DATABASE_URL` starting with `postgres://` and automatically normalizes it to `postgresql://` before connecting.

### 2. Strict Production Safety Enforcement
* **Problem**: Accidentally deploying code to production with placeholder authentication credentials.
* **Fix**: If `ENVIRONMENT` is set to `production`, a `model_validator` runs at startup. If `SECRET_KEY` or `API_KEY` match standard local development defaults (e.g., `supersecretkeyplaceholder` or `devapikey123`), the application **crashes immediately** with a configuration error.

---

## Managing Environments

### 1. Local Development (`development`)
* Place variables inside the `.env` file in the project root.
* Local development defaults to a local SQLite database (`sqlite:///./payment.db`).
* Logs are printed as readable, colorized command line blocks.

### 2. Containerized / Cloud Deployments (`production`)
* Do **not** package the `.env` file into production container images.
* Pass settings directly as system environment variables (e.g. on AWS ECS, Kubernetes Secrets, Heroku Config Vars).
* Ensure `ENVIRONMENT` is set to `production` and you provide secure, randomized values for `SECRET_KEY` and `API_KEY`.
* Logs are printed as structured JSON lines.
