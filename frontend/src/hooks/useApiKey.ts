"use client";
import { useState, useEffect } from "react";
import type { ApiKeyConfig } from "@/types";

const STORAGE_KEY = "formula_fuse_api_key";

export function useApiKey() {
  const [config, setConfig] = useState<ApiKeyConfig>({ provider: "openai", key: "" });

  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setConfig(JSON.parse(stored));
      } catch {}
    }
  }, []);

  const save = (c: ApiKeyConfig) => {
    setConfig(c);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(c));
  };

  const clear = () => {
    setConfig({ provider: "openai", key: "" });
    sessionStorage.removeItem(STORAGE_KEY);
  };

  return { config, save, clear, hasKey: !!config.key };
}
