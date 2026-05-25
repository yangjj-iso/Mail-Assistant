"use client";

import { useEffect, useCallback } from "react";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";

interface InterviewReminder {
  id: number;
  company: string;
  position: string;
  next_time: string;
  next_round: string;
  location: string;
  type: "1h" | "24h" | "soon";
}

function requestNotificationPermission() {
  if (typeof window !== "undefined" && "Notification" in window) {
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
  }
}

function showBrowserNotification(title: string, body: string) {
  if (typeof window !== "undefined" && "Notification" in window) {
    if (Notification.permission === "granted") {
      new Notification(title, { body, icon: "/favicon.ico" });
    }
  }
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    requestNotificationPermission();
  }, []);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "interview_reminder") {
      const data = msg.data as InterviewReminder;
      const time = new Date(data.next_time);
      const timeStr = time.toLocaleString("zh-CN", {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });

      let urgency = "";
      if (data.type === "1h") {
        urgency = "1 小时后";
      } else if (data.type === "24h") {
        urgency = "明天";
      } else {
        urgency = "即将开始";
      }

      const title = `面试提醒: ${data.company}`;
      const body = `${data.position} ${data.next_round || ""}\n${timeStr} ${data.location || ""}`;

      showBrowserNotification(title, body);

      toast(title, {
        description: `${urgency} - ${data.position} ${data.next_round || ""}\n${timeStr}`,
        duration: 10000,
        action: {
          label: "查看",
          onClick: () => {
            window.location.href = "/schedule";
          },
        },
      });
    }
  }, []);

  useWebSocket(handleWsMessage);

  return <>{children}</>;
}
