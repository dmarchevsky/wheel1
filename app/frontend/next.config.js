/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost'],
  },
  // Proxy API requests to backend during development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'development' 
          ? 'http://localhost:8000/:path*' 
          : '/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
