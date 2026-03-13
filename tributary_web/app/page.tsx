"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="bg-mist min-h-screen flex items-center justify-center">
      <div className="bg-sand animate-pulse rounded-card w-64 h-8" />
    </div>
  );
}
