"use client";
import { useState } from "react";
import type { ApiKeyConfig } from "@/types";

interface Props {
  current: ApiKeyConfig;
  onSave: (c: ApiKeyConfig) => void;
  onClose: () => void;
}

export function ApiKeyModal({ current, onSave, onClose }: Props) {
  const [provider, setProvider] = useState<ApiKeyConfig["provider"]>(current.provider);
  const [key, setKey] = useState(current.key);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ provider, key });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <h2 className="text-lg font-bold mb-1">API Key 設定 (BYOK)</h2>
        <p className="text-xs text-gray-500 mb-4">
          APIキーはブラウザのセッションにのみ保存され、サーバーには送信されません。
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">AIプロバイダー</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as ApiKeyConfig["provider"])}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              <option value="openai">OpenAI (GPT-4o mini 推奨)</option>
              <option value="claude">Claude (Haiku 推奨)</option>
              <option value="gemini">Gemini (Flash 推奨)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={provider === "openai" ? "sk-..." : provider === "claude" ? "sk-ant-..." : "AIza..."}
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono"
              required
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700"
            >
              保存
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 border rounded-lg text-sm hover:bg-gray-50"
            >
              キャンセル
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
