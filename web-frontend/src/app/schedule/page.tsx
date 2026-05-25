"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "motion/react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { fetchUpcoming, getApplicationICalUrl, type Application } from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";

function extractVideoLink(location: string): string | null {
  const patterns = [
    /https?:\/\/[^\s]*(?:zoom|meeting|teams|webex|feishu|dingtalk|tencent)[^\s]*/i,
    /https?:\/\/t\.zijieimg\.com\/[^\s]+/i,
    /https?:\/\/meeting\.[^\s]+/i,
  ];
  for (const pattern of patterns) {
    const match = location.match(pattern);
    if (match) return match[0];
  }
  return null;
}

export default function SchedulePage() {
  const [upcoming, setUpcoming] = useState<Application[]>([]);

  const loadData = useCallback(async () => {
    try {
      const data = await fetchUpcoming();
      setUpcoming(data || []);
    } catch (err) {
      console.error("Failed to load upcoming:", err);
      setUpcoming([]);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "job_update") {
      loadData();
    }
  }, [loadData]);

  useWebSocket(handleWsMessage);

  const handleExportICal = (app: Application) => {
    const url = getApplicationICalUrl(app.id);
    window.open(url, "_blank");
    toast("正在下载日历文件");
  };

  const now = new Date();

  return (
    <div className="p-6 max-w-3xl">
      <TextGenerateEffect words="面试日程" className="text-2xl mb-6" />

      {upcoming.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          暂无近期面试安排。当收到面试邀约邮件时，日程会自动更新。
        </p>
      ) : (
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
          <div className="space-y-4 pl-10">
            {upcoming.map((app, i) => {
              const isPast = app.next_time
                ? new Date(app.next_time) < now
                : false;
              const videoLink = app.location ? extractVideoLink(app.location) : null;
              return (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className="relative">
                    <div
                      className={`absolute -left-[26px] top-3 w-3 h-3 rounded-full border-2 ${
                        isPast
                          ? "bg-muted border-muted-foreground/30"
                          : "bg-primary border-primary"
                      }`}
                    />
                    <Card className={isPast ? "opacity-50" : ""}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold">{app.company}</p>
                            <p className="text-sm text-muted-foreground">{app.position}</p>
                            {app.next_round && (
                              <Badge variant="outline" className="mt-1 text-xs">
                                {app.next_round}
                              </Badge>
                            )}
                          </div>
                          <div className="text-right shrink-0">
                            {app.next_time && (
                              <p className="text-sm font-medium">
                                {new Date(app.next_time).toLocaleDateString("zh-CN", {
                                  month: "short",
                                  day: "numeric",
                                  weekday: "short",
                                })}
                              </p>
                            )}
                            {app.next_time && (
                              <p className="text-xs text-muted-foreground">
                                {new Date(app.next_time).toLocaleTimeString("zh-CN", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </p>
                            )}
                          </div>
                        </div>
                        {app.location && (
                          <p className="text-xs text-muted-foreground mt-2">{app.location}</p>
                        )}
                        <div className="flex gap-2 mt-3">
                          {videoLink && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => window.open(videoLink, "_blank")}
                            >
                              <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                              加入会议
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => handleExportICal(app)}
                          >
                            <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                              <line x1="16" y1="2" x2="16" y2="6" />
                              <line x1="8" y1="2" x2="8" y2="6" />
                              <line x1="3" y1="10" x2="21" y2="10" />
                            </svg>
                            导出日历
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
