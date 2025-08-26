# Environment Configuration

This project supports two distinct environments: **Development** and **Production**, each with its own configuration and Docker Compose setup.

## Environment Files

### Development Environment (`env.dev`)
- **Purpose**: Local development with hot-reloading
- **Logging**: DEBUG level for verbose output
- **Hot Reloading**: Enabled for both frontend and backend
- **Volume Mounts**: Source code mounted for real-time development
- **URLs**: Configured for nginx proxy (`http://localhost`)

### Production Environment (`.env`)
- **Purpose**: Production deployment
- **Logging**: INFO level for performance
- **Hot Reloading**: Disabled for stability
- **Built Images**: Optimized production images
- **URLs**: Production URLs and configurations

## Docker Compose Files

### Development (`infra/docker-compose.yml`)
- **Environment File**: `env.dev`
- **Dockerfiles**: `Dockerfile.backend.dev`, `Dockerfile.frontend.dev`
- **Features**: Hot-reloading, volume mounts, development dependencies
- **Ports**: Exposed for direct access and debugging

### Production (`infra/docker-compose.prod.yml`)
- **Environment File**: `.env`
- **Dockerfiles**: `Dockerfile.backend`, `Dockerfile.frontend`
- **Features**: Optimized builds, restart policies, production settings
- **Ports**: Only nginx exposed (port 80)

## Just Commands

### Development Commands
```bash
just dev              # Start development environment with hot-reloading
just dev-direct       # Start without nginx proxy
just dev-backend      # Start backend services only
just dev-frontend     # Start frontend only
```

### Production Commands
```bash
just build            # Build production images
just deploy           # Deploy to production
just prod             # Start production environment (for testing)
just prod-stop        # Stop production environment
```

### Monitoring Commands

#### Development Monitoring
```bash
just logs             # Show all development logs
just logs-api         # Show API logs (development)
just logs-frontend    # Show frontend logs (development)
just health           # Check development services health
```

#### Production Monitoring
```bash
just logs-prod        # Show all production logs
just logs-prod-api    # Show API logs (production)
just logs-prod-frontend # Show frontend logs (production)
just health-prod      # Check production services health
```

### Utility Commands
```bash
just clean            # Clean up development environment
just clean-prod       # Clean up production environment
just clean-cache      # Clear development Redis cache
just clean-cache-prod # Clear production Redis cache
```

## Environment Variables

### Required for Both Environments
```bash
# Tradier API (Required)
TRADIER_ACCESS_TOKEN=your_token
TRADIER_ACCOUNT_ID=your_account_id

# Database (Can use defaults)
POSTGRES_PASSWORD=secure_password

# Optional Services
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
OPENAI_API_KEY=your_openai_key
```

### Development-Specific (`env.dev`)
```bash
ENV=dev
LOG_LEVEL=DEBUG
WEB_BASE_URL=http://localhost
API_BASE_URL=http://localhost/api
```

### Production-Specific (`.env`)
```bash
ENV=production
LOG_LEVEL=INFO
WEB_BASE_URL=https://yourdomain.com
API_BASE_URL=https://yourdomain.com/api
```

## Workflow Examples

### Development Workflow
```bash
# 1. Setup (first time only)
just setup

# 2. Configure environment
nano env.dev  # Add your API keys

# 3. Start development
just dev

# 4. Make changes and see them immediately
# Edit files in app/backend/ or app/frontend/

# 5. Monitor
just logs-api
just health

# 6. Clean up
just clean
```

### Production Workflow
```bash
# 1. Configure production environment
nano .env  # Add your production API keys

# 2. Build and deploy
just build
just deploy

# 3. Monitor production
just logs-prod
just health-prod

# 4. Stop when needed
just prod-stop
```

## Key Differences

| Feature | Development | Production |
|---------|-------------|------------|
| **Environment File** | `env.dev` | `.env` |
| **Docker Compose** | `docker-compose.yml` | `docker-compose.prod.yml` |
| **Dockerfiles** | `*.dev` variants | Standard production variants |
| **Hot Reloading** | ✅ Enabled | ❌ Disabled |
| **Volume Mounts** | ✅ Source code | ❌ Built images |
| **Logging** | DEBUG level | INFO level |
| **Ports** | Multiple exposed | Only nginx (80) |
| **Restart Policy** | None | `unless-stopped` |
| **Performance** | Optimized for dev | Optimized for prod |

## Best Practices

### Development
1. **Always use `env.dev`** for development
2. **Use `just dev`** as your primary development command
3. **Monitor logs** with `just logs-api` and `just logs-frontend`
4. **Test changes** before committing
5. **Use hot-reloading** for faster development cycles

### Production
1. **Always use `.env`** for production
2. **Test production builds** with `just prod` before deploying
3. **Monitor production** with `just logs-prod`
4. **Use proper secrets management** for production credentials
5. **Backup data** before major deployments

### Environment Management
1. **Never commit** `.env` or `env.dev` files (they're in `.gitignore`)
2. **Use `env.example`** as a template for both environments
3. **Keep environments separate** - don't mix dev and prod configurations
4. **Document changes** when updating environment configurations
5. **Test both environments** before releasing

## Troubleshooting

### Development Issues
```bash
# Check if development environment is running
just health

# View development logs
just logs

# Restart development environment
just clean
just dev
```

### Production Issues
```bash
# Check if production environment is running
just health-prod

# View production logs
just logs-prod

# Restart production environment
just prod-stop
just deploy
```

### Environment File Issues
```bash
# Verify environment file syntax
cat env.dev | grep -v "^#" | grep -v "^$"
cat .env | grep -v "^#" | grep -v "^$"

# Check for missing variables
grep -E "REPLACE_ME|your_" env.dev
grep -E "REPLACE_ME|your_" .env
```

