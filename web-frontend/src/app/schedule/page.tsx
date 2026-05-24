"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "motion/react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { fetchUpcoming, type Application } from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";

const MOCK_UPCOMING: Application[] = [
  {
    id: 1,
    account_id: 1,
    company: "字节跳动",
    position: "后端开发实习生-飞书办公套件",
    stage: "interview",
    last_email_id: 1,
    next_time: "2026-05-11T15:00:00+08:00",
    next_round: "一面",
    location: "视频面试（飞书）",
    notes: "",
    created_at: "2026-04-28T10:00:00Z",
    updated_at: "2026-05-09T09:00:00Z",
  },
  {
    id: 2,
    account_id: 1,
    company: "腾讯",
    position: "全栈开发工程师",
    stage: "interview",
    last_email_id: 2,
    next_time: "2026-05-30T10:00:00Z",
    next_round: "HR面",
    location: "深圳市南山区",
    notes: "",
    created_at: "2026-05-01T08:00:00Z",
    updated_at: "2026-05-22T11:00:00Z",
  },
];

export default function SchedulePage() {
  const [upcoming, setUpcoming] = useState<Application[]>([]);

  const loadData = useCallback(async () => {
    try {
      const data = await fetchUpcoming();
      setUpcoming(data && data.length > 0 ? data : MOCK_UPCOMING);
    } catch {
      setUpcoming(MOCK_UPCOMING);
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
                    <Card
                      className={isPast ? "opacity-50" : ""}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold">
                              {app.company}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {app.position}
                            </p>
                            {app.next_round && (
                              <Badge variant="outline" className="mt-1 text-xs">
                                {app.next_round}
                              </Badge>
                            )}
                          </div>
                          <div className="text-right shrink-0">
                            {app.next_time && (
                              <p className="text-sm font-medium">
                                {new Date(app.next_time).toLocaleDateString(
                                  "zh-CN",
                                  {
                                    month: "short",
                                    day: "numeric",
                                    weekday: "short",
                                  }
                                )}
                              </p>
                            )}
                            {app.next_time && (
                              <p className="text-xs text-muted-foreground">
                                {new Date(app.next_time).toLocaleTimeString(
                                  "zh-CN",
                                  { hour: "2-digit", minute: "2-digit" }
                                )}
                              </p>
                            )}
                          </div>
                        </div>
                        {app.location && (
                          <p className="text-xs text-muted-foreground mt-2">
                            {app.location}
                          </p>
                        )}
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
