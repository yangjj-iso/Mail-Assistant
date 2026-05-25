"use client";

import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import {
  fetchApplications,
  updateApplication,
  deleteApplication,
  fetchApplicationEmails,
  type Application,
  type Email,
} from "@/lib/api";
import { useWebSocket, type WsMessage } from "@/lib/use-websocket";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const STAGES = ["applied", "written_test", "interview", "offer", "rejected"] as const;
type Stage = (typeof STAGES)[number];

const STAGE_CONFIG: Record<Stage, { label: string; color: string; bgColor: string }> = {
  applied: { label: "已投递", color: "text-blue-600", bgColor: "bg-blue-50" },
  written_test: { label: "笔试", color: "text-purple-600", bgColor: "bg-purple-50" },
  interview: { label: "面试", color: "text-amber-600", bgColor: "bg-amber-50" },
  offer: { label: "Offer", color: "text-green-600", bgColor: "bg-green-50" },
  rejected: { label: "未通过", color: "text-red-600", bgColor: "bg-red-50" },
};

/* PLACEHOLDER_KANBAN_CARD */

interface KanbanCardProps {
  app: Application;
  onDelete: (id: number) => void;
  onClick: (app: Application) => void;
}

function KanbanCard({ app, onDelete, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: app.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onClick(app)}
      className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm cursor-grab active:cursor-grabbing hover:border-gray-300 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">{app.company}</p>
          <p className="text-xs text-gray-500 mt-0.5 truncate">{app.position}</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 text-gray-400 hover:text-red-500 shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(app.id);
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </Button>
      </div>
      {app.next_round && (
        <Badge variant="outline" className="mt-2 text-[10px] h-5">
          {app.next_round}
        </Badge>
      )}
      {app.next_time && (
        <p className="text-[10px] text-gray-400 mt-1">
          {new Date(app.next_time).toLocaleString("zh-CN", {
            month: "numeric",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      )}
    </div>
  );
}

/* PLACEHOLDER_KANBAN_COLUMN */

interface KanbanColumnProps {
  stage: Stage;
  apps: Application[];
  onDelete: (id: number) => void;
  onCardClick: (app: Application) => void;
}

function KanbanColumn({ stage, apps, onDelete, onCardClick }: KanbanColumnProps) {
  const config = STAGE_CONFIG[stage];
  const { setNodeRef, isOver } = useDroppable({ id: stage });

  return (
    <div className="flex flex-col min-w-[240px] w-[240px] shrink-0">
      <div className={`rounded-t-lg px-3 py-2 ${config.bgColor}`}>
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
          <Badge variant="secondary" className="h-5 text-[10px]">
            {apps.length}
          </Badge>
        </div>
      </div>
      <div
        ref={setNodeRef}
        className={`flex-1 rounded-b-lg p-2 min-h-[400px] transition-colors ${
          isOver ? "bg-blue-100 ring-2 ring-blue-400" : "bg-gray-50"
        }`}
      >
        <SortableContext items={apps.map((a) => a.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {apps.map((app) => (
              <KanbanCard key={app.id} app={app} onDelete={onDelete} onClick={onCardClick} />
            ))}
          </div>
        </SortableContext>
        {apps.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-8">拖拽卡片到此处</p>
        )}
      </div>
    </div>
  );
}

/* PLACEHOLDER_MAIN_COMPONENT */

export default function KanbanPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [relatedEmails, setRelatedEmails] = useState<Email[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [notes, setNotes] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  );

  const loadApps = useCallback(async () => {
    try {
      const res = await fetchApplications();
      setApps(res.items || []);
    } catch (err) {
      console.error("Failed to load applications:", err);
      setApps([]);
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

  const handleCardClick = async (app: Application) => {
    setSelectedApp(app);
    setNotes(app.notes || "");
    setDialogOpen(true);
    try {
      const emails = await fetchApplicationEmails(app.id);
      setRelatedEmails(emails || []);
    } catch {
      setRelatedEmails([]);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedApp) return;
    try {
      await updateApplication(selectedApp.id, { notes });
      setApps((prev) =>
        prev.map((a) => (a.id === selectedApp.id ? { ...a, notes } : a))
      );
      toast("备注已保存");
    } catch {
      toast.error("保存失败");
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    const app = apps.find((a) => a.id === event.active.id);
    setActiveApp(app || null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveApp(null);
    const { active, over } = event;
    if (!over) return;

    const draggedApp = apps.find((a) => a.id === active.id);
    if (!draggedApp) return;

    const overId = over.id;
    let targetStage: Stage | null = null;

    if (STAGES.includes(overId as Stage)) {
      targetStage = overId as Stage;
    } else {
      const overApp = apps.find((a) => a.id === overId);
      if (overApp) {
        targetStage = overApp.stage as Stage;
      }
    }

    if (targetStage && targetStage !== draggedApp.stage) {
      setApps((prev) =>
        prev.map((a) => (a.id === draggedApp.id ? { ...a, stage: targetStage! } : a))
      );

      try {
        await updateApplication(draggedApp.id, { stage: targetStage });
        toast(`已更新: ${draggedApp.company} → ${STAGE_CONFIG[targetStage].label}`);
      } catch {
        setApps((prev) =>
          prev.map((a) => (a.id === draggedApp.id ? { ...a, stage: draggedApp.stage } : a))
        );
        toast.error("更新失败");
      }
    }
  };

  const groupedApps = STAGES.reduce(
    (acc, stage) => {
      acc[stage] = apps.filter((a) => a.stage === stage);
      return acc;
    },
    {} as Record<Stage, Application[]>
  );

  return (
    <div className="h-screen overflow-hidden flex flex-col p-6">
      <TextGenerateEffect words="求职看板" className="text-2xl mb-4 shrink-0" />
      <p className="text-sm text-muted-foreground mb-4 shrink-0">
        拖拽卡片到不同列以更新申请状态
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4 min-w-max pb-4">
            {STAGES.map((stage) => (
              <KanbanColumn
                key={stage}
                stage={stage}
                apps={groupedApps[stage]}
                onDelete={handleDelete}
                onCardClick={handleCardClick}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeApp && (
            <div className="bg-white rounded-lg border-2 border-blue-400 p-3 shadow-lg w-[220px]">
              <p className="text-sm font-medium text-gray-900">{activeApp.company}</p>
              <p className="text-xs text-gray-500 mt-0.5">{activeApp.position}</p>
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedApp?.company} - {selectedApp?.position}</DialogTitle>
          </DialogHeader>
          {selectedApp && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">阶段:</span>
                  <Badge className="ml-2" variant="outline">
                    {STAGE_CONFIG[selectedApp.stage as Stage]?.label || selectedApp.stage}
                  </Badge>
                </div>
                {selectedApp.next_round && (
                  <div>
                    <span className="text-gray-500">轮次:</span>
                    <span className="ml-2">{selectedApp.next_round}</span>
                  </div>
                )}
                {selectedApp.location && (
                  <div>
                    <span className="text-gray-500">地点:</span>
                    <span className="ml-2">{selectedApp.location}</span>
                  </div>
                )}
                {selectedApp.next_time && (
                  <div>
                    <span className="text-gray-500">时间:</span>
                    <span className="ml-2">
                      {new Date(selectedApp.next_time).toLocaleString("zh-CN")}
                    </span>
                  </div>
                )}
              </div>

              <Separator />

              <div>
                <label className="text-sm text-gray-500 block mb-1">备注</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full h-20 p-2 text-sm border rounded-md resize-none"
                  placeholder="添加备注..."
                />
              </div>

              {relatedEmails.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="text-sm text-gray-500 mb-2">关联邮件 ({relatedEmails.length})</p>
                    <div className="space-y-2 max-h-32 overflow-auto">
                      {relatedEmails.map((email) => (
                        <div key={email.ID} className="text-xs p-2 bg-gray-50 rounded">
                          <p className="font-medium truncate">{email.subject}</p>
                          <p className="text-gray-400">
                            {new Date(email.date).toLocaleDateString("zh-CN")}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              关闭
            </Button>
            <Button onClick={handleSaveNotes}>保存备注</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
