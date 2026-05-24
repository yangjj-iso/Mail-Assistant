"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { fetchEmails, type Email } from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { toast } from "sonner";

const LABELS = [
  "all",
  "spam",
  "forum",
  "promotions",
  "social_media",
  "updates",
  "verify_code",
];

const LABEL_NAMES: Record<string, string> = {
  all: "全部",
  spam: "垃圾邮件",
  forum: "论坛",
  promotions: "推广",
  social_media: "社交媒体",
  updates: "通知更新",
  verify_code: "验证码",
};

const LABEL_COLORS: Record<string, string> = {
  spam: "bg-red-100 text-red-800",
  ham: "bg-green-100 text-green-800",
  forum: "bg-blue-100 text-blue-800",
  promotions: "bg-yellow-100 text-yellow-800",
  social_media: "bg-purple-100 text-purple-800",
  updates: "bg-cyan-100 text-cyan-800",
  verify_code: "bg-orange-100 text-orange-800",
};

const MOCK_EMAILS: Email[] = [
  {
    ID: 1,
    account_id: 1,
    message_id: "msg-1",
    subject: "字节跳动校园招聘-后端开发实习生-飞书办公套件 面试邀约",
    from_addr: "campus@bytedance.com",
    date: "2026-05-09T09:00:00Z",
    body_preview: "杨俊杰：字节跳动诚邀你参加字节跳动校园招聘-后端开发实习生-飞书办公套件岗位的面试，感谢你的耐心等待。\n\n【面试信息】\n面试形式：视频面试\n面试时间：2026-05-11 15:00(GMT+08:00)\n面试链接：https://t.zijieimg.com/85dcwD4JSvI/",
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
    body_preview: "您好，恭喜您通过腾讯全栈开发工程师技术面试，现邀请您参加HR面试。\n\n时间：2026-05-30 10:00\n地点：深圳市南山区腾讯大厦",
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
    body_preview: "恭喜您！经过综合评估，我们很高兴地通知您已通过阿里巴巴Java开发工程师岗位的全部面试环节。请查收附件中的Offer详情。",
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
    body_preview: "尊敬的用户，双十一大促活动火热进行中，全场满300减50，更有限时秒杀等你来抢！",
    stage1_label: "ham",
    stage2_label: "promotions",
    final_label: "promotions",
    classified_at: "2026-05-07T10:00:01Z",
  },
  {
    ID: 6,
    account_id: 1,
    message_id: "msg-6",
    subject: "You have won a free iPhone 15!",
    from_addr: "prize@scam-mail.xyz",
    date: "2026-05-06T08:00:00Z",
    body_preview: "Congratulations! You have been selected to receive a free iPhone 15. Click here to claim your prize now!",
    stage1_label: "spam",
    stage2_label: null,
    final_label: "spam",
    classified_at: "2026-05-06T08:00:01Z",
  },
  {
    ID: 7,
    account_id: 1,
    message_id: "msg-7",
    subject: "Re: [GitHub] Discussion on React 19 features",
    from_addr: "notifications@github.com",
    date: "2026-05-05T12:00:00Z",
    body_preview: "@user mentioned you in a discussion about React 19 Server Components...",
    stage1_label: "ham",
    stage2_label: "forum",
    final_label: "forum",
    classified_at: "2026-05-05T12:00:01Z",
  },
  {
    ID: 8,
    account_id: 1,
    message_id: "msg-8",
    subject: "小红书: 你关注的博主发布了新内容",
    from_addr: "notify@xiaohongshu.com",
    date: "2026-05-04T18:00:00Z",
    body_preview: "你关注的博主「前端小王子」发布了新笔记：《2026前端面试必备知识点》",
    stage1_label: "ham",
    stage2_label: "social_media",
    final_label: "social_media",
    classified_at: "2026-05-04T18:00:01Z",
  },
];

export default function InboxPage() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [activeLabel, setActiveLabel] = useState("all");
  const [selected, setSelected] = useState<Email | null>(null);
  const size = 20;

  const loadEmails = useCallback(async () => {
    try {
      const res = await fetchEmails({
        page,
        size,
        label: activeLabel === "all" ? undefined : activeLabel,
      });
      if (res?.items?.length > 0) {
        setEmails(res.items);
        setTotal(res.total);
        return;
      }
    } catch {
      // backend offline
    }
    const filtered = activeLabel === "all"
      ? MOCK_EMAILS
      : MOCK_EMAILS.filter((e) => e.final_label === activeLabel);
    setEmails(filtered);
    setTotal(filtered.length);
  }, [page, activeLabel]);

  useEffect(() => {
    loadEmails();
  }, [loadEmails]);

  const handleWsMessage = useCallback(
    (msg: WsMessage) => {
      if (msg.type === "new_email") {
        const email = msg.data as Email;
        toast(`新邮件: ${email.subject}`, {
          description: `来自 ${email.from_addr}`,
        });
        if (page === 1) {
          if (activeLabel === "all" || email.final_label === activeLabel) {
            setEmails((prev) => [email, ...prev.slice(0, size - 1)]);
            setTotal((t) => t + 1);
          }
        }
      }
    },
    [page, activeLabel]
  );

  useWebSocket(handleWsMessage);

  const totalPages = Math.ceil(total / size);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top filter tabs - fixed */}
      <div className="border-b px-4 py-2 flex items-center gap-2 flex-wrap shrink-0">
        <TextGenerateEffect words="收件箱" className="text-lg mr-2" />
        {LABELS.map((label) => (
          <button
            key={label}
            onClick={() => { setActiveLabel(label); setPage(1); }}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
              activeLabel === label
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted text-muted-foreground"
            }`}
          >
            {LABEL_NAMES[label] || label}
          </button>
        ))}
      </div>

      {/* Main content: list + detail */}
      <div className="flex flex-1 min-h-0">
        {/* Email list */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex-1 overflow-auto min-h-0">
            {emails.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-muted-foreground">该分类下暂无邮件</p>
              </div>
            ) : (
            <div className="divide-y">
              <AnimatePresence initial={false} mode="popLayout">
                {emails.map((email, idx) => (
                  <motion.div
                    key={`${activeLabel}-${email.ID ?? idx}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setSelected(email)}
                    className={`px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                      selected?.ID === email.ID ? "bg-muted" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {email.subject || "(无主题)"}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {email.from_addr} · {new Date(email.date).toLocaleDateString()}
                        </p>
                      </div>
                      <Badge
                        className={`shrink-0 ${LABEL_COLORS[email.final_label] || "bg-gray-100 text-gray-800"}`}
                      >
                        {LABEL_NAMES[email.final_label] || email.final_label}
                      </Badge>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            )}
          </div>

          {/* Pagination */}
          <div className="border-t px-4 py-2 flex items-center justify-between shrink-0">
            <span className="text-sm text-muted-foreground">
              共 {total} 封邮件
            </span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                上一页
              </Button>
              <span className="text-sm">{page} / {totalPages || 1}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                下一页
              </Button>
            </div>
          </div>
        </div>

        {/* Detail panel */}
        {selected && (
          <>
            <Separator orientation="vertical" />
            <div className="w-[420px] shrink-0 p-5 overflow-auto">
              <div className="space-y-4">
                <h2 className="text-base font-semibold leading-snug break-words">
                  {selected.subject}
                </h2>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>发件人：{selected.from_addr}</p>
                  <p>日期：{new Date(selected.date).toLocaleString()}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={LABEL_COLORS[selected.final_label] || "bg-gray-100 text-gray-800"}>
                    {LABEL_NAMES[selected.final_label] || selected.final_label}
                  </Badge>
                  {selected.stage1_label && (
                    <Badge variant="outline">一级: {selected.stage1_label}</Badge>
                  )}
                  {selected.stage2_label && (
                    <Badge variant="outline">二级: {selected.stage2_label}</Badge>
                  )}
                </div>
                <Separator />
                <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">
                  {selected.body_preview}
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
