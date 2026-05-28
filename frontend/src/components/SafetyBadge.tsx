import type { SafetyStatus } from "@/types";
import { safetyEmoji } from "@/lib/utils";

interface Props {
  status: SafetyStatus;
  size?: "sm" | "md" | "lg";
}

const colors: Record<SafetyStatus, string> = {
  Green: "bg-green-100 text-green-800 border border-green-200",
  Yellow: "bg-yellow-100 text-yellow-800 border border-yellow-200",
  Red: "bg-red-100 text-red-800 border border-red-200",
  Black: "bg-gray-900 text-white border border-gray-700",
};

const sizes = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-3 py-1",
  lg: "text-base px-4 py-2 font-bold",
};

export function SafetyBadge({ status, size = "md" }: Props) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${colors[status]} ${sizes[size]}`}>
      {safetyEmoji(status)} {status}
    </span>
  );
}
