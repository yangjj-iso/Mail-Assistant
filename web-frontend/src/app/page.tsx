"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "motion/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WobbleCard } from "@/components/ui/wobble-card";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { fetchStats, fetchEmails, fetchJobStats, fetchUpcoming, type LabelStat, type Email, type JobStats, type Application } from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";

const LABEL_COLORS: Record<string, string> = {
  spam: "bg-red-100 text-red-800",
  ham: "bg-green-100 text-green-800",
  forum: "bg-blue-100 text-blue-800",
  promotions: "bg-yellow-100 text-yellow-800",
  social_media: "bg-purple-100 text-purple-800",
  updates: "bg-cyan-100 text-cyan-800",
  verify_code: "bg-orange-100 text-orange-800",
};

const LABEL_BG: Record<string, string> = {
  spam: "bg-red-900",
  ham: "bg-green-900",
  forum: "bg-blue-900",
  promotions: "bg-yellow-900",
  social_media: "bg-purple-900",
  updates: "bg-cyan-900",
  verify_code: "bg-orange-900",
};

const MOCK_STATS: LabelStat[] = [
  { label: "updates", count: 12 },
  { label: "promotions", count: 8 },
  { label: "spam", count: 5 },
  { label: "forum", count: 3 },
  { label: "verify_code", count: 4 },
  { label: "social_media", count: 2 },
];

const MOCK_EMAILS: Email[] = [
  {
    ID: 1,
    account_id: 1,
    message_id: "msg-1",
    subject: "字节跳动校园招聘-后端开发实习生-飞书办公套件 面试邀约",
    from_addr: "campus@bytedance.com",
    date: "2026-05-09T09:00:00Z",
    body_preview: "杨俊杰：字节跳动诚邀你参加字节跳动校园招聘-后端开发实习生-飞书办公套件岗位的面试...",
    stage1_label: "ham",
    stage2_label: "updates",
    final_label: "updates",
    classified_at: "2026-05-09T09:00:01Z",
  },
  {
    ID: 2,
    account_id: 1,
    message_id: "msg-2",
    subject: "腾讯HR面试通知",
    from_addr: "hr@tencent.com",
    date: "2026-05-22T11:00:00Z",
    body_preview: "您好，恭喜您通过腾讯全栈开发工程师技术面试，现邀请您参加HR面...",
    stage1_label: "ham",
    stage2_label: "updates",
    final_label: "updates",
    classified_at: "2026-05-22T11:00:01Z",
  },
  {
    ID: 3,
    account_id: 1,
    message_id: "msg-3",
    subject: "阿里巴巴Offer发放通知",
    from_addr: "offer@alibaba.com",
    date: "2026-05-18T16:00:00Z",
    body_preview: "恭喜您！经过综合评估，我们很高兴地通知您已通过阿里巴巴Java开发工程师岗位的全部面试...",
    stage1_label: "ham",
    stage2_label: "updates",
    final_label: "updates",
    classified_at: "2026-05-18T16:00:01Z",
  },
  {
    ID: 4,
    account_id: 1,
    message_id: "msg-4",
    subject: "【验证码】您的登录验证码为 892341",
    from_addr: "noreply@163.com",
    date: "2026-05-08T14:30:00Z",
    body_preview: "您的验证码为 892341，5分钟内有效，请勿泄露给他人。",
    stage1_label: "ham",
    stage2_label: "verify_code",
    final_label: "verify_code",
    classified_at: "2026-05-08T14:30:01Z",
  },
  {
    ID: 5,
    account_id: 1,
    message_id: "msg-5",
    subject: "双十一大促提前享，满300减50",
    from_addr: "promo@jd.com",
    date: "2026-05-07T10:00:00Z",
    body_preview: "尊敬的用户，双十一大促活动火热进行中...",
    stage1_label: "ham",
    stage2_label: "promotions",
    final_label: "promotions",
    classified_at: "2026-05-07T10:00:01Z",
  },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<LabelStat[]>([]);
  const [recentEmails, setRecentEmails] = useState<Email[]>([]);
  const [jobStats, setJobStats] = useState<JobStats | null>(null);
  const [upcomingInterviews, setUpcomingInterviews] = useState<Application[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [s, e, js, ui] = await Promise.all([
        fetchStats(),
        fetchEmails({ page: 1, size: 10 }),
        fetchJobStats().catch(() => null),
        fetchUpcoming().catch(() => []),
      ]);
      setStats(s && s.length > 0 ? s : MOCK_STATS);
      setRecentEmails(e.items && e.items.length > 0 ? e.items : MOCK_EMAILS);
      setJobStats(js);
      setUpcomingInterviews(ui.slice(0, 3));
    } catch {
      setStats(MOCK_STATS);
      setRecentEmails(MOCK_EMAILS);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "new_email") {
      const email = msg.data as Email;
      toast(`新邮件: ${email.subject}`, {
        description: `分类为 ${email.final_label}`,
      });
      setRecentEmails((prev) => [email, ...prev.slice(0, 9)]);
      setStats((prev) => {
        const existing = prev.find((s) => s.label === email.final_label);
        if (existing) {
          return prev.map((s) =>
            s.label === email.final_label ? { ...s, count: s.count + 1 } : s
          );
        }
        return [...prev, { label: email.final_label, count: 1 }];
      });
    }
  }, []);

  useWebSocket(handleWsMessage);

  const total = stats.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="p-6 space-y-6 h-screen overflow-auto">
      <TextGenerateEffect words="仪表盘" className="text-2xl" />

      {/* Stats grid using Aceternity WobbleCards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <WobbleCard containerClassName="bg-slate-800 min-h-[120px]" className="p-4 py-8">
          <p className="text-xs text-slate-300">邮件总数</p>
          <motion.p
            key={total}
            initial={{ scale: 1.3, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-3xl font-bold text-white mt-1"
          >
            {total}
          </motion.p>
        </WobbleCard>
        {stats.map((stat) => (
          <WobbleCard
            key={stat.label}
            containerClassName={`${LABEL_BG[stat.label] || "bg-indigo-800"} min-h-[120px]`}
            className="p-4 py-8"
          >
            <p className="text-xs text-slate-300 capitalize">
              {stat.label.replace("_", " ")}
            </p>
            <motion.p
              key={stat.count}
              initial={{ scale: 1.3, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-3xl font-bold text-white mt-1"
            >
              {stat.count}
            </motion.p>
          </WobbleCard>
        ))}
      </div>

      {/* Job Stats Section */}
      {jobStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <p className="text-xs text-blue-600">进行中申请</p>
              <p className="text-2xl font-bold text-blue-800">{jobStats.active}</p>
            </CardContent>
          </Card>
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="p-4">
              <p className="text-xs text-amber-600">本周面试</p>
              <p className="text-2xl font-bold text-amber-800">{jobStats.week_interviews}</p>
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-4">
              <p className="text-xs text-green-600">Offer</p>
              <p className="text-2xl font-bold text-green-800">{jobStats.offers}</p>
            </CardContent>
          </Card>
          <Card className="bg-red-50 border-red-200">
            <CardContent className="p-4">
              <p className="text-xs text-red-600">未通过</p>
              <p className="text-2xl font-bold text-red-800">{jobStats.rejected}</p>
            </CardContent>
          </Card>
          <Card className="bg-slate-50 border-slate-200">
            <CardContent className="p-4">
              <p className="text-xs text-slate-600">总申请数</p>
              <p className="text-2xl font-bold text-slate-800">{jobStats.total}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Upcoming Interviews */}
      {upcomingInterviews.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              近期面试
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {upcomingInterviews.map((app) => (
                <div key={app.id} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium">{app.company}</p>
                    <p className="text-xs text-muted-foreground">{app.position} {app.next_round && `- ${app.next_round}`}</p>
                  </div>
                  {app.next_time && (
                    <div className="text-right">
                      <p className="text-sm font-medium">
                        {new Date(app.next_time).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(app.next_time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent emails */}
      <Card>
        <CardHeader>
          <CardTitle>最近邮件</CardTitle>
        </CardHeader>
        <CardContent>
          {recentEmails.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              暂无邮件。请在设置中添加邮箱账号。
            </p>
          ) : (
            <div className="space-y-3">
              {recentEmails.map((email, i) => (
                <motion.div
                  key={email.ID || i}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between border-b pb-2 last:border-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">
                      {email.subject || "(无主题)"}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {email.from_addr}
                    </p>
                  </div>
                  <Badge
                    className={
                      LABEL_COLORS[email.final_label] || "bg-gray-100 text-gray-800"
                    }
                  >
                    {email.final_label}
                  </Badge>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}