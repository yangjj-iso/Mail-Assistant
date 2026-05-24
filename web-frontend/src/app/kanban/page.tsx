"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import {
  fetchApplications,
  deleteApplication,
  type Application,
} from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";

const STAGES = [
  "applied",
  "written_test",
  "first_interview",
  "second_interview",
  "hr_interview",
  "offer",
];

const STAGE_CONFIG: Record<string, { label: string; icon: string }> = {
  applied: { label: "投递简历", icon: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" },
  written_test: { label: "笔试", icon: "M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" },
  first_interview: { label: "一面", icon: "M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4-4v2M12 7a4 4 0 100-8 4 4 0 000 8z" },
  second_interview: { label: "二面", icon: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2M9 7a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" },
  hr_interview: { label: "HR面", icon: "M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2M8.5 7a4 4 0 100-8 4 4 0 000 8zM20 8v6M23 11h-6" },
  offer: { label: "Offer", icon: "M22 11.08V12a10 10 0 11-5.93-9.14M22 4L12 14.01l-3-3" },
};

// Map backend stage + next_round to display stage
function resolveDisplayStage(stage: string, nextRound: string): string {
  if (stage === "offer") return "offer";
  if (stage === "applied") return "applied";
  if (stage === "written_test") return "written_test";
  if (stage === "interview") {
    const r = nextRound.toLowerCase();
    if (r.includes("hr")) return "hr_interview";
    if (r.includes("二") || r.includes("2") || r.includes("复")) return "second_interview";
    return "first_interview";
  }
  return "applied";
}

const MOCK_APPS: Application[] = [
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
  {
    id: 3,
    account_id: 1,
    company: "阿里巴巴",
    position: "Java开发工程师",
    stage: "offer",
    last_email_id: 3,
    next_time: null,
    next_round: "",
    location: "杭州市余杭区",
    notes: "",
    created_at: "2026-04-15T09:00:00Z",
    updated_at: "2026-05-18T16:00:00Z",
  },
  {
    id: 4,
    account_id: 1,
    company: "美团",
    position: "后端开发工程师",
    stage: "interview",
    last_email_id: 4,
    next_time: "2026-05-25T14:00:00Z",
    next_round: "二面",
    location: "北京市朝阳区望京",
    notes: "",
    created_at: "2026-04-20T10:00:00Z",
    updated_at: "2026-05-20T10:00:00Z",
  },
  {
    id: 5,
    account_id: 1,
    company: "小红书",
    position: "Go开发工程师",
    stage: "rejected",
    last_email_id: 5,
    next_time: null,
    next_round: "一面",
    location: "",
    notes: "一面未通过",
    created_at: "2026-04-10T10:00:00Z",
    updated_at: "2026-05-05T10:00:00Z",
  },
];

function ProgressTimeline({
  currentStage,
  updatedAt,
}: {
  currentStage: string;
  updatedAt: string;
}) {
  const currentIdx = STAGES.indexOf(currentStage);
  const visibleStages = STAGES.slice(0, currentIdx + 1);

  return (
    <div className="flex items-start gap-0.5">
      {visibleStages.map((stage, i) => {
        const config = STAGE_CONFIG[stage];
        const isCurrent = i === currentIdx;

        return (
          <div key={stage} className="flex items-start">
            <div className="flex flex-col items-center w-[68px]">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center bg-blue-50 border-2 border-blue-400"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={config.icon} />
                </svg>
              </div>
              <p className="text-[11px] mt-1 text-center text-blue-600 font-medium">
                {config.label}
              </p>
              {isCurrent && (
                <p className="text-[10px] text-gray-400 mt-0.5">
                  {new Date(updatedAt).toLocaleDateString("zh-CN")}
                </p>
              )}
            </div>
            {i < visibleStages.length - 1 && (
              <div className="flex items-center h-10">
                <div className="w-4 h-px bg-blue-300" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function KanbanPage() {
  const [apps, setApps] = useState<Application[]>([]);

  const loadApps = useCallback(async () => {
    try {
      const res = await fetchApplications();
      const items = res.items || [];
      setApps(items.length > 0 ? items : MOCK_APPS);
    } catch {
      setApps(MOCK_APPS);
    }
  }, []);

  useEffect(() => {
    loadApps();
  }, [loadApps]);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "job_update") {
      const app = msg.data as Application;
      toast(`求职更新: ${app.company} - ${app.position}`);
      setApps((prev) => {
        const idx = prev.findIndex((a) => a.id === app.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = app;
          return next;
        }
        return [app, ...prev];
      });
    }
  }, []);

  useWebSocket(handleWsMessage);

  const handleDelete = async (id: number) => {
    await deleteApplication(id);
    setApps((prev) => prev.filter((a) => a.id !== id));
    toast("已删除");
  };

  return (
    <div className="h-screen overflow-auto p-6">
      <TextGenerateEffect words="求职看板" className="text-2xl mb-6" />

      {apps.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          暂无求职记录。当收到求职相关邮件时，会自动创建追踪记录。
        </p>
      ) : (
        <div className="space-y-3">
          {apps.map((app, i) => {
            const isRejected = app.stage === "rejected";
            const displayStage = isRejected
              ? resolveDisplayStage("interview", app.next_round)
              : resolveDisplayStage(app.stage, app.next_round);

            return (
              <motion.div
                key={app.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <div
                  className={`rounded-lg border bg-white p-5 transition-colors ${
                    isRejected ? "border-red-100 opacity-60" : "border-gray-100 hover:border-gray-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {app.company}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {app.position}
                        </p>
                      </div>
                      {isRejected && (
                        <Badge variant="destructive" className="text-[10px] h-5">
                          未通过
                        </Badge>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-gray-400 h-7 px-2"
                      onClick={() => handleDelete(app.id)}
                    >
                      删除
                    </Button>
                  </div>
                  <ProgressTimeline
                    currentStage={displayStage}
                    updatedAt={app.updated_at}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
