"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import {
  fetchAccounts,
  createAccount,
  deleteAccount,
  type Account,
} from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";

const PRESETS: Record<string, { host: string; port: number }> = {
  "163": { host: "imap.163.com", port: 993 },
  qq: { host: "imap.qq.com", port: 993 },
  gmail: { host: "imap.gmail.com", port: 993 },
  outlook: { host: "outlook.office365.com", port: 993 },
};

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [preset, setPreset] = useState("163");
  const [loading, setLoading] = useState(false);

  const loadAccounts = useCallback(async () => {
    const data = await fetchAccounts();
    setAccounts(data);
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "account_status") {
      const data = msg.data as { id: number; status: string };
      setAccounts((prev) =>
        prev.map((a) => (a.ID === data.id ? { ...a, status: data.status } : a))
      );
    }
  }, []);

  useWebSocket(handleWsMessage);

  const handleAdd = async () => {
    if (!email || !password) {
      toast.error("请填写邮箱地址和授权码");
      return;
    }
    setLoading(true);
    try {
      const p = PRESETS[preset];
      await createAccount({
        email,
        password,
        imap_host: p.host,
        imap_port: p.port,
      });
      toast.success("账号已添加");
      setEmail("");
      setPassword("");
      loadAccounts();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "添加账号失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteAccount(id);
    toast.success("账号已移除");
    loadAccounts();
  };

  return (
    <div className="h-screen overflow-auto">
      <BackgroundBeamsWithCollision className="h-32 md:h-40 rounded-none">
        <TextGenerateEffect words="账号设置" className="text-2xl md:text-3xl text-center relative z-10" />
      </BackgroundBeamsWithCollision>

      <div className="p-6 space-y-6 max-w-2xl">

      <Card>
        <CardHeader>
          <CardTitle>添加邮箱账号</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>邮箱服务商</Label>
            <Select value={preset} onValueChange={(v) => v && setPreset(v)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="163">163 邮箱</SelectItem>
                <SelectItem value="qq">QQ 邮箱</SelectItem>
                <SelectItem value="gmail">Gmail</SelectItem>
                <SelectItem value="outlook">Outlook</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>邮箱地址</Label>
            <Input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>授权码 / 密码</Label>
            <Input
              type="password"
              placeholder="IMAP 授权码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              163/QQ 邮箱请使用 IMAP 授权码，不是登录密码。
            </p>
          </div>
          <Button onClick={handleAdd} disabled={loading}>
            {loading ? "添加中..." : "添加账号"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已连接账号</CardTitle>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              暂无已配置的账号。
            </p>
          ) : (
            <div className="space-y-3">
              {accounts.map((acc) => (
                <div
                  key={acc.ID}
                  className="flex items-center justify-between border rounded-md p-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{acc.email}</p>
                    <p className="text-xs text-muted-foreground">
                      {acc.imap_host}:{acc.imap_port}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        acc.status === "connected" ? "default" : "secondary"
                      }
                    >
                      {acc.status}
                    </Badge>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(acc.ID)}
                    >
                      移除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
