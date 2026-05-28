import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { SafetyStatus, AtomType } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function safetyColor(status: SafetyStatus): string {
  return {
    Green: "bg-green-100 text-green-800 border-green-300",
    Yellow: "bg-yellow-100 text-yellow-800 border-yellow-300",
    Red: "bg-red-100 text-red-800 border-red-300",
    Black: "bg-gray-900 text-white border-gray-700",
  }[status];
}

export function safetyBadgeColor(status: SafetyStatus): string {
  return {
    Green: "bg-green-500",
    Yellow: "bg-yellow-500",
    Red: "bg-red-500",
    Black: "bg-gray-900",
  }[status];
}

export function atomTypeColor(type: AtomType): string {
  return {
    ingredient: "bg-orange-100 text-orange-700",
    microbe: "bg-purple-100 text-purple-700",
    enzyme: "bg-blue-100 text-blue-700",
    condition: "bg-teal-100 text-teal-700",
    goal: "bg-pink-100 text-pink-700",
    process: "bg-gray-100 text-gray-700",
  }[type];
}

export function atomTypeLabel(type: AtomType): string {
  return {
    ingredient: "原材料",
    microbe: "菌",
    enzyme: "酵素",
    condition: "条件",
    goal: "目的",
    process: "工程",
  }[type];
}

export function safetyEmoji(status: SafetyStatus): string {
  return { Green: "✅", Yellow: "⚠️", Red: "🔴", Black: "⛔" }[status];
}
