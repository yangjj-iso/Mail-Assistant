package model

import (
	"time"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

type Account struct {
	ID                uint      `json:"id" gorm:"primaryKey"`
	Email             string    `json:"email" gorm:"uniqueIndex;not null"`
	IMAPHost          string    `json:"imap_host" gorm:"not null"`
	IMAPPort          int       `json:"imap_port" gorm:"default:993"`
	EncryptedPassword string    `json:"-" gorm:"not null"`
	Status            string    `json:"status" gorm:"default:disconnected"`
	CreatedAt         time.Time `json:"created_at"`
}

type Email struct {
	ID            uint      `json:"id" gorm:"primaryKey"`
	AccountID     uint      `json:"account_id" gorm:"index"`
	MessageID     string    `json:"message_id" gorm:"uniqueIndex"`
	Subject       string    `json:"subject"`
	FromAddr      string    `json:"from_addr"`
	Date          time.Time `json:"date"`
	BodyPreview   string    `json:"body_preview"`
	Stage1Label   string    `json:"stage1_label"`
	Stage2Label   *string   `json:"stage2_label"`
	FinalLabel    string    `json:"final_label"`
	ClassifiedAt  time.Time `json:"classified_at"`
	IsJob         bool      `json:"is_job" gorm:"default:false"`
	JobStage      string    `json:"job_stage,omitempty"`
	Entities      string    `json:"entities,omitempty"`
	ApplicationID *uint     `json:"application_id,omitempty" gorm:"index"`
}

type Application struct {
	ID          uint       `json:"id" gorm:"primaryKey"`
	AccountID   uint       `json:"account_id" gorm:"index"`
	Company     string     `json:"company" gorm:"not null"`
	Position    string     `json:"position" gorm:"not null"`
	Stage       string     `json:"stage" gorm:"default:applied"`
	LastEmailID uint       `json:"last_email_id"`
	NextTime    *time.Time `json:"next_time,omitempty"`
	NextRound   string     `json:"next_round,omitempty"`
	Location    string     `json:"location,omitempty"`
	Notes       string     `json:"notes,omitempty"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
}

func InitDB(path string) (*gorm.DB, error) {
	db, err := gorm.Open(sqlite.Open(path), &gorm.Config{})
	if err != nil {
		return nil, err
	}
	if err := db.AutoMigrate(&Account{}, &Email{}, &Application{}); err != nil {
		return nil, err
	}
	return db, nil
}
