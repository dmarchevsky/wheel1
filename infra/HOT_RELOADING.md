# Hot Reloading Development Setup

## Overview

This project now supports hot-reloading for both frontend and backend development, eliminating the need to rebuild containers when making code changes.

## How It Works

### Backend Hot Reloading
- Uses `uvicorn` with `--reload` flag
- Volume mounts the backend code directory
- Automatically restarts when Python files change
- Excludes `__pycache__` and `.pytest_cache` directories

### Frontend Hot Reloading
- Uses Next.js development server
- Volume mounts the frontend code directory
- Preserves `node_modules` and `.next` directories
- Automatically refreshes browser on file changes

## Development Workflow

### 1. Start Development Environment
```bash
just dev
```

This starts all services with hot-reloading enabled:
- Backend API with uvicorn reload
- Frontend with Next.js dev server
- Database and Redis
- Nginx reverse proxy

### 2. Make Code Changes
Simply edit files in your IDE:
- Backend changes in `app/backend/` will auto-restart the API
- Frontend changes in `app/frontend/` will auto-refresh the browser

### 3. View Logs
```bash
just logs-api      # Backend logs
just logs-frontend # Frontend logs
just logs          # All logs
```

## File Structure for Hot Reloading

```
app/
├── backend/           # Backend code (hot-reloaded)
│   ├── main.py
│   ├── routers/
│   ├── services/
│   └── ...
└── frontend/          # Frontend code (hot-reloaded)
    ├── src/
    ├── package.json
    └── ...
```

## Volume Mounts

### Backend
```yaml
volumes:
  - ../app/backend:/app          # Source code
  - /app/__pycache__            # Exclude cache
  - /app/.pytest_cache          # Exclude test cache
```

### Frontend
```yaml
volumes:
  - ../app/frontend:/app        # Source code
  - /app/node_modules           # Preserve dependencies
  - /app/.next                  # Preserve build cache
```

## Development Commands

### Start Different Services
```bash
just dev              # All services with hot-reloading
just dev-direct       # Without nginx proxy
just dev-backend      # Backend services only
just dev-frontend     # Frontend only
```

### Monitoring
```bash
just logs-api         # Backend logs
just logs-frontend    # Frontend logs
just health           # Check all services
```

### Code Quality
```bash
just lint             # Run all linters
just format           # Format all code
just test             # Run all tests
```

## Environment Configuration

The development environment uses `env.dev` with:
- `LOG_LEVEL=DEBUG` for verbose logging
- `ENV=dev` for development mode
- Proper URLs for nginx proxy

## Troubleshooting

### Backend Not Reloading
1. Check if uvicorn is running with reload flag
2. Verify volume mounts are correct
3. Check file permissions
4. Look at logs: `just logs-api`

### Frontend Not Reloading
1. Check if Next.js dev server is running
2. Verify volume mounts are correct
3. Check browser console for errors
4. Look at logs: `just logs-frontend`

### Common Issues

1. **Port conflicts**
   ```bash
   sudo lsof -i :8000  # Check if port 8000 is in use
   sudo lsof -i :3000  # Check if port 3000 is in use
   ```

2. **Permission issues**
   ```bash
   sudo chown -R $USER:$USER app/
   ```

3. **Cache issues**
   ```bash
   just clean-cache    # Clear Redis cache
   docker system prune # Clear Docker cache
   ```

## Performance Tips

1. **Exclude unnecessary files** from volume mounts
2. **Use .dockerignore** to exclude files from build context
3. **Monitor resource usage** with `docker stats`
4. **Restart services** if they become unresponsive

## Production vs Development

| Feature | Development | Production |
|---------|-------------|------------|
| Hot Reloading | ✅ Enabled | ❌ Disabled |
| Volume Mounts | ✅ Source code | ❌ Built images |
| Logging | DEBUG level | INFO level |
| CORS | Permissive | Restricted |
| Performance | Optimized for dev | Optimized for prod |

## Best Practices

1. **Always use `just dev`** for development
2. **Check logs** when making changes
3. **Test changes** before committing
4. **Use proper environment files** (`env.dev` vs `.env`)
5. **Monitor resource usage** during development

