# Changelog

## [2024-01-XX] - Hot Reloading Development Setup

### 🚀 New Features

#### Hot Reloading Support
- **Backend Hot Reloading**: Added uvicorn with `--reload` flag for automatic API server restart on code changes
- **Frontend Hot Reloading**: Next.js development server with automatic browser refresh
- **Volume Mounts**: Source code directories mounted for real-time development
- **Cache Exclusion**: Proper exclusion of `__pycache__`, `.pytest_cache`, `node_modules`, and `.next` directories

#### Development Dockerfiles
- **`Dockerfile.backend.dev`**: Development-specific backend image with hot-reloading dependencies
- **`Dockerfile.frontend.dev`**: Development-specific frontend image with Next.js dev server
- **`docker-compose.dev.yml`**: Dedicated development compose file (optional)

#### Environment Management
- **`env.dev`**: Development-specific environment file with DEBUG logging
- **Separate Configurations**: Clear separation between development and production environments
- **Optimized URLs**: Proper configuration for nginx proxy setup

### 🔧 Improvements

#### Docker Compose Cleanup
- **Consolidated Files**: Reduced from 3 to 2 Docker Compose files
- **Clear Separation**: Development (`docker-compose.yml`) vs Production (`docker-compose.prod.yml`)
- **Environment Files**: Development uses `env.dev`, Production uses `.env`
- **Proper Dockerfiles**: Development uses `*.dev` variants, Production uses standard variants

#### Justfile Optimization
- **Organized Structure**: Commands grouped by functionality (Development, Production, Testing, etc.)
- **Removed Redundancy**: Eliminated duplicate and unnecessary commands
- **Better Documentation**: Comprehensive help system with categorized commands
- **Development Focus**: Primary commands optimized for hot-reloading workflow
- **Environment-Specific Commands**: Clear separation between dev and prod commands

#### Docker Configuration
- **Volume Mounts**: Added proper volume mounts for hot-reloading
- **Environment Files**: Updated to use `env.dev` for development
- **Health Checks**: Maintained comprehensive health checking
- **Dependencies**: Added development dependencies (uvicorn[standard], watchdog)

#### Nginx Proxy Integration
- **CORS Solution**: Maintained nginx reverse proxy for CORS-free development
- **Unified Access**: Single entry point at `http://localhost`
- **API Routing**: `/api/*` requests properly routed to backend
- **Health Monitoring**: Dedicated health check endpoints

### 📚 Documentation

#### New Documentation Files
- **`infra/HOT_RELOADING.md`**: Comprehensive guide for hot-reloading setup
- **`infra/ENVIRONMENTS.md`**: Complete guide for development vs production environments
- **`scripts/dev-setup.sh`**: Automated development environment setup script
- **`CHANGELOG.md`**: This changelog documenting all changes

#### Updated Documentation
- **`SETUP.md`**: Updated with hot-reloading instructions
- **`infra/NGINX_PROXY.md`**: Enhanced with development workflow
- **`justfile`**: Complete reorganization with better help system

### 🛠️ Development Workflow

#### New Commands
```bash
just setup              # Initial development setup
just dev               # Start with hot-reloading (recommended)
just dev-direct        # Start without nginx proxy
just dev-backend       # Start backend services only
just dev-frontend      # Start frontend only
```

#### Improved Monitoring
```bash
just logs-api          # Backend logs with hot-reload info
just logs-frontend     # Frontend logs with Next.js dev info
just health            # Comprehensive health checking
```

### 🔄 Migration Guide

#### For Existing Users
1. **Update Environment**: Copy `env.example` to `env.dev` and configure
2. **Use New Commands**: Replace old commands with new optimized ones
3. **Enjoy Hot Reloading**: No more container rebuilds for code changes

#### For New Users
1. **Run Setup**: `just setup` for automated initial configuration
2. **Configure API Keys**: Edit `env.dev` with your credentials
3. **Start Development**: `just dev` for full hot-reloading experience

### 🎯 Benefits

#### Developer Experience
- **Faster Development**: No container rebuilds required
- **Real-time Feedback**: Immediate code change reflection
- **Better Debugging**: DEBUG level logging in development
- **Simplified Workflow**: Single command to start everything

#### Performance
- **Optimized Builds**: Development and production images separated
- **Efficient Caching**: Proper volume mount exclusions
- **Resource Management**: Better resource utilization

#### Maintainability
- **Clear Separation**: Development vs production configurations
- **Comprehensive Testing**: Enhanced test and health check commands
- **Better Documentation**: Extensive guides and examples

### 🐛 Bug Fixes

- **Environment Variables**: Fixed URL configurations for nginx proxy
- **Volume Mounts**: Proper exclusion of cache directories
- **Health Checks**: Improved reliability and accuracy
- **Logging**: Better log levels and formatting

### 📋 Technical Details

#### Backend Changes
- **uvicorn reload**: Enabled with `--reload` and `--reload-dir` flags
- **Volume mounts**: `../app/backend:/app` with cache exclusions
- **Dependencies**: Added `uvicorn[standard]` and `watchdog`

#### Frontend Changes
- **Next.js dev server**: Development mode with hot-reloading
- **Volume mounts**: `../app/frontend:/app` with dependency preservation
- **Environment**: `NODE_ENV=development` configuration

#### Infrastructure Changes
- **Docker Compose**: Updated with development-specific configurations
- **Environment Files**: Separate `env.dev` for development
- **Nginx**: Maintained proxy functionality with hot-reloading support

---

## Previous Versions

### [2024-01-XX] - Initial Nginx Proxy Setup
- Added nginx reverse proxy for CORS elimination
- Implemented unified access point at `http://localhost`
- Created comprehensive proxy testing and monitoring
- Added production-ready docker-compose configuration
