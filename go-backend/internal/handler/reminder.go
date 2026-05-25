package handler

import (
	"log"
	"time"

	"mail-classifier/internal/model"
	"mail-classifier/internal/ws"

	"gorm.io/gorm"
)

type ReminderService struct {
	db     *gorm.DB
	hub    *ws.Hub
	stopCh chan struct{}
}

func NewReminderService(db *gorm.DB, hub *ws.Hub) *ReminderService {
	return &ReminderService{
		db:     db,
		hub:    hub,
		stopCh: make(chan struct{}),
	}
}

func (r *ReminderService) Start() {
	go r.run()
}

func (r *ReminderService) Stop() {
	close(r.stopCh)
}

func (r *ReminderService) run() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	r.checkAndNotify()

	for {
		select {
		case <-r.stopCh:
			return
		case <-ticker.C:
			r.checkAndNotify()
		}
	}
}

func (r *ReminderService) checkAndNotify() {
	now := time.Now()
	in24h := now.Add(24 * time.Hour)
	in1h := now.Add(1 * time.Hour)

	var apps []model.Application
	r.db.Where("next_time IS NOT NULL AND next_time > ? AND next_time < ?", now, in24h).
		Order("next_time ASC").
		Find(&apps)

	for _, app := range apps {
		if app.NextTime == nil {
			continue
		}

		timeUntil := app.NextTime.Sub(now)
		var reminderType string

		if timeUntil <= time.Hour && timeUntil > 50*time.Minute {
			reminderType = "1h"
		} else if timeUntil <= 24*time.Hour && timeUntil > 23*time.Hour {
			reminderType = "24h"
		} else if app.NextTime.Before(in1h) && app.NextTime.After(now) {
			reminderType = "soon"
		} else {
			continue
		}

		log.Printf("[Reminder] %s interview at %s (%s)", app.Company, app.NextTime.Format("2006-01-02 15:04"), reminderType)

		r.hub.Broadcast(ws.Message{
			Type: "interview_reminder",
			Data: map[string]interface{}{
				"id":         app.ID,
				"company":    app.Company,
				"position":   app.Position,
				"next_time":  app.NextTime,
				"next_round": app.NextRound,
				"location":   app.Location,
				"type":       reminderType,
			},
		})
	}
}

func (r *ReminderService) TriggerCheck() {
	r.checkAndNotify()
}
