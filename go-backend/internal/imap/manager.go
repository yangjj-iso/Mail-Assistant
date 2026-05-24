package imap

import (
	"log"
	"sync"

	"mail-classifier/internal/classifier"
	"mail-classifier/internal/model"
	"mail-classifier/internal/ws"

	"gorm.io/gorm"
)

type Manager struct {
	mu         sync.Mutex
	watchers   map[uint]*Watcher
	db         *gorm.DB
	classifier *classifier.Client
	hub        *ws.Hub
	decryptFn  func(string) (string, error)
}

func NewManager(db *gorm.DB, cl *classifier.Client, hub *ws.Hub, decryptFn func(string) (string, error)) *Manager {
	return &Manager{
		watchers:   make(map[uint]*Watcher),
		db:         db,
		classifier: cl,
		hub:        hub,
		decryptFn:  decryptFn,
	}
}

func (m *Manager) StartAll() {
	var accounts []model.Account
	m.db.Find(&accounts)
	for _, acc := range accounts {
		m.StartAccount(acc)
	}
	log.Printf("[IMAP Manager] started %d watchers", len(accounts))
}

func (m *Manager) StartAccount(account model.Account) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.watchers[account.ID]; exists {
		return
	}

	password, err := m.decryptFn(account.EncryptedPassword)
	if err != nil {
		log.Printf("[IMAP Manager] decrypt password for %s failed: %v", account.Email, err)
		return
	}

	w := NewWatcher(account, password, m.db, m.classifier, m.hub)
	m.watchers[account.ID] = w
	w.Start()
	log.Printf("[IMAP Manager] started watcher for %s", account.Email)
}

func (m *Manager) StopAccount(accountID uint) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if w, exists := m.watchers[accountID]; exists {
		w.Stop()
		delete(m.watchers, accountID)
		log.Printf("[IMAP Manager] stopped watcher for account %d", accountID)
	}
}

func (m *Manager) StopAll() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for id, w := range m.watchers {
		w.Stop()
		delete(m.watchers, id)
	}
	log.Println("[IMAP Manager] all watchers stopped")
}
