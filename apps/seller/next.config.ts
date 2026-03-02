import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/identity/:path*",
        destination: "http://localhost:8001/:path*",
      },
      {
        source: "/api/course/:path*",
        destination: "http://localhost:8002/:path*",
      },
      {
        source: "/api/payment/:path*",
        destination: "http://localhost:8004/:path*",
      },
      {
        source: "/api/notification/:path*",
        destination: "http://localhost:8005/:path*",
      },
    ];
  },
};

export default nextConfig;
