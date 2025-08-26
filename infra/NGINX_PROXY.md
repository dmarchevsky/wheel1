# Nginx Reverse Proxy Setup

## Overview

This project includes an nginx reverse proxy to eliminate CORS (Cross-Origin Resource Sharing) issues and provide a unified entry point for the application.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │    │   Nginx Proxy   │    │   Backend API   │
│                 │    │   (Port 80)     │    │   (Port 8000)   │
│ http://localhost│───▶│                 │───▶│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Frontend      │
                       │   (Port 3000)   │
                       │                 │
                       └─────────────────┘
```

## URL Structure

- **Frontend**: `http://localhost/` (served by nginx)
- **API**: `http://localhost/api/*` (proxied to backend)
- **Health Check**: `http://localhost/health` (nginx health endpoint)

## CORS Solution

The nginx proxy eliminates CORS issues by:

1. **Single Origin**: All requests come from the same origin (`http://localhost`)
2. **Automatic CORS Headers**: nginx adds appropriate CORS headers to API responses
3. **Preflight Handling**: OPTIONS requests are handled automatically
4. **No Browser CORS**: Since everything is served from the same origin, browsers don't enforce CORS

## Configuration Details

### Nginx Configuration (`infra/nginx.conf`)

- **API Proxy**: Routes `/api/*` requests to the backend service
- **CORS Headers**: Automatically added to all API responses
- **Rate Limiting**: 10 requests/second with burst allowance
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.
- **Gzip Compression**: Enabled for better performance
- **WebSocket Support**: For Next.js development mode

### Frontend Configuration

The frontend is configured to use the proxy:
- `NEXT_PUBLIC_API_BASE_URL=http://localhost/api`
- Next.js rewrites for development mode

## Development Workflow

### With Proxy (Recommended)
```bash
just dev                    # Start with nginx proxy
just test-proxy            # Test proxy functionality
just health                # Check all services
```

### Without Proxy (Direct Access)
```bash
just dev-without-proxy     # Start without nginx
# Access directly:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
```

## Production Deployment

The production setup uses the same nginx proxy:

```bash
just build                 # Build production images
just deploy               # Deploy with nginx proxy
```

## Testing the Proxy

Run the test script to verify everything is working:

```bash
just test-proxy
```

This will test:
- Nginx health endpoint
- API health via proxy
- CORS headers
- Frontend accessibility
- Direct API access (should still work)

## Troubleshooting

### Common Issues

1. **Port 80 already in use**
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2  # or other service using port 80
   ```

2. **CORS still occurring**
   - Ensure you're accessing via `http://localhost` not `http://localhost:3000`
   - Check that API calls use `/api/` prefix

3. **Nginx not starting**
   ```bash
   just logs-nginx
   docker logs wheel_nginx
   ```

### Health Checks

```bash
just health-nginx          # Check nginx health
just health-api            # Check API via proxy
just health-frontend       # Check frontend via proxy
```

## Benefits

1. **No CORS Issues**: Eliminates cross-origin problems
2. **Single Entry Point**: One URL for the entire application
3. **Security**: Centralized security headers and rate limiting
4. **Performance**: Gzip compression and caching
5. **Production Ready**: Same setup for development and production
6. **Flexibility**: Can still access services directly if needed

## Security Features

- Rate limiting (10 req/s with burst)
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Request sanitization
- Logging and monitoring
- Health checks

## Performance Features

- Gzip compression
- Connection pooling
- Timeout management
- Caching headers
- Efficient routing

