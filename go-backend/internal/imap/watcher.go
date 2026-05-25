package imap

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strings"
	"time"

	"mail-classifier/internal/classifier"
	"mail-classifier/internal/model"
	"mail-classifier/internal/ws"

	imapClient "github.com/emersion/go-imap"
	"github.com/emersion/go-imap/client"
	"github.com/emersion/go-message/mail"
	"gorm.io/gorm"
)

type Watcher struct {
	account    model.Account
	password   string
	db         *gorm.DB
	classifier *classifier.Client
	hub        *ws.Hub
	stopCh     chan struct{}
}

func NewWatcher(account model.Account, password string, db *gorm.DB, cl *classifier.Client, hub *ws.Hub) *Watcher {
	return &Watcher{
		account:    account,
		password:   password,
		db:         db,
		classifier: cl,
		hub:        hub,
		stopCh:     make(chan struct{}),
	}
}

func (w *Watcher) Start() {
	go w.run()
}

func (w *Watcher) Stop() {
	close(w.stopCh)
}

func (w *Watcher) run() {
	backoff := time.Second
	for {
		select {
		case <-w.stopCh:
			return
		default:
		}

		err := w.connectAndWatch()
		if err != nil {
			log.Printf("[IMAP] %s error: %v, reconnecting in %v", w.account.Email, err, backoff)
			w.updateStatus("error")
		}

		select {
		case <-w.stopCh:
			return
		case <-time.After(backoff):
		}
		if backoff < 2*time.Minute {
			backoff *= 2
		}
	}
}

func (w *Watcher) connectAndWatch() error {
	addr := fmt.Sprintf("%s:%d", w.account.IMAPHost, w.account.IMAPPort)
	c, err := client.DialTLS(addr, nil)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer c.Logout()

	if err := c.Login(w.account.Email, w.password); err != nil {
		return fmt.Errorf("login: %w", err)
	}

	mbox, err := c.Select("INBOX", false)
	if err != nil {
		return fmt.Errorf("select inbox: %w", err)
	}

	w.updateStatus("connected")
	w.hub.Broadcast(ws.Message{Type: "account_status", Data: map[string]interface{}{
		"id": w.account.ID, "email": w.account.Email, "status": "connected",
	}})

	// Fetch recent emails
	if mbox.Messages > 0 {
		from := uint32(1)
		if mbox.Messages > 30 {
			from = mbox.Messages - 29
		}
		seqSet := new(imapClient.SeqSet)
		seqSet.AddRange(from, mbox.Messages)
		w.fetchAndClassify(c, seqSet)
	}

	// IDLE loop
	for {
		select {
		case <-w.stopCh:
			return nil
		default:
		}

		stop := make(chan struct{})
		done := make(chan error, 1)
		go func() {
			done <- c.Idle(stop, nil)
		}()

		select {
		case <-w.stopCh:
			close(stop)
			return nil
		case err := <-done:
			if err != nil {
				return fmt.Errorf("idle: %w", err)
			}
		case <-time.After(25 * time.Minute):
			close(stop)
			<-done
		}

		// Check for new messages after IDLE returns
		status, err := c.Select("INBOX", false)
		if err != nil {
			return fmt.Errorf("re-select: %w", err)
		}
		if status.Messages > mbox.Messages {
			seqSet := new(imapClient.SeqSet)
			seqSet.AddRange(mbox.Messages+1, status.Messages)
			w.fetchAndClassify(c, seqSet)
			mbox = status
		}
	}
}

func (w *Watcher) fetchAndClassify(c *client.Client, seqSet *imapClient.SeqSet) {
	section := &imapClient.BodySectionName{}
	items := []imapClient.FetchItem{section.FetchItem(), imapClient.FetchEnvelope}

	messages := make(chan *imapClient.Message, 50)
	go func() {
		if err := c.Fetch(seqSet, items, messages); err != nil {
			log.Printf("[IMAP] %s fetch error: %v", w.account.Email, err)
		}
	}()

	for msg := range messages {
		w.processMessage(msg, section)
	}
}

func (w *Watcher) processMessage(msg *imapClient.Message, section *imapClient.BodySectionName) {
	if msg == nil || msg.Envelope == nil {
		return
	}

	env := msg.Envelope
	messageID := env.MessageId
	if messageID == "" {
		messageID = fmt.Sprintf("%s-%d", w.account.Email, msg.SeqNum)
	}

	// Skip if already processed
	var count int64
	w.db.Model(&model.Email{}).Where("message_id = ?", messageID).Count(&count)
	if count > 0 {
		return
	}

	subject := env.Subject
	fromAddr := ""
	if len(env.From) > 0 {
		fromAddr = env.From[0].Address()
	}
	date := env.Date

	// Extract body
	body := ""
	r := msg.GetBody(section)
	if r != nil {
		body = extractTextBody(r)
	}

	// Classify
	text := subject + " " + body
	if strings.TrimSpace(text) == "" {
		text = subject
	}

	result, err := w.classifier.Predict(text)
	if err != nil {
		log.Printf("[Classify] %s error: %v", messageID, err)
		return
	}

	preview := body
	runes := []rune(preview)
	if len(runes) > 200 {
		preview = string(runes[:200])
	}

	finalLabel := result.Stage1Label
	if result.Stage2Label != nil && *result.Stage2Label != "" {
		finalLabel = *result.Stage2Label
	}

	// Job classification
	jobResult, err := w.classifier.PredictJob(body, subject)
	if err != nil {
		log.Printf("[JobClassify] %s error: %v", messageID, err)
	}
	isJob := jobResult != nil && jobResult.IsJob

	email := model.Email{
		AccountID:    w.account.ID,
		MessageID:    messageID,
		Subject:      subject,
		FromAddr:     fromAddr,
		Date:         date,
		BodyPreview:  preview,
		Stage1Label:  result.Stage1Label,
		Stage2Label:  result.Stage2Label,
		FinalLabel:   finalLabel,
		ClassifiedAt: time.Now(),
	}

	if isJob {
		email.IsJob = true
		email.JobStage = jobResult.Stage
		entJSON, _ := json.Marshal(jobResult.Entities)
		email.Entities = string(entJSON)
	}

	if err := w.db.Create(&email).Error; err != nil {
		log.Printf("[DB] save email error: %v", err)
		return
	}

	// Create or update Application if job email
	if email.IsJob && jobResult != nil {
		w.upsertApplication(&email, jobResult)
	}

	w.hub.Broadcast(ws.Message{Type: "new_email", Data: email})
}

func (w *Watcher) upsertApplication(email *model.Email, jobResult *classifier.JobPredictResponse) {
	company := ""
	position := ""
	if len(jobResult.Entities.Company) > 0 {
		company = jobResult.Entities.Company[0]
	}
	if len(jobResult.Entities.Position) > 0 {
		position = jobResult.Entities.Position[0]
	}
	if company == "" && position == "" {
		return
	}

	var app model.Application
	query := w.db.Where("account_id = ?", w.account.ID)
	if company != "" {
		query = query.Where("company = ?", company)
	}
	if position != "" {
		query = query.Where("position = ?", position)
	}

	err := query.First(&app).Error
	if err == gorm.ErrRecordNotFound {
		app = model.Application{
			AccountID:   w.account.ID,
			Company:     company,
			Position:    position,
			Stage:       jobResult.Stage,
			LastEmailID: email.ID,
		}
		if len(jobResult.Entities.Time) > 0 {
			// Store as string in NextRound for now; proper parsing would need date parsing
			app.NextRound = strings.Join(jobResult.Entities.Round, ", ")
		}
		if len(jobResult.Entities.Location) > 0 {
			app.Location = jobResult.Entities.Location[0]
		}
		w.db.Create(&app)
	} else if err == nil {
		app.Stage = jobResult.Stage
		app.LastEmailID = email.ID
		if len(jobResult.Entities.Location) > 0 {
			app.Location = jobResult.Entities.Location[0]
		}
		if len(jobResult.Entities.Round) > 0 {
			app.NextRound = jobResult.Entities.Round[0]
		}
		w.db.Save(&app)
	}

	if app.ID > 0 {
		appID := app.ID
		email.ApplicationID = &appID
		w.db.Save(email)
		w.hub.Broadcast(ws.Message{Type: "job_update", Data: app})
	}
}

func extractTextBody(r io.Reader) string {
	mr, err := mail.CreateReader(r)
	if err != nil {
		return readAll(r)
	}
	var textBody string
	for {
		p, err := mr.NextPart()
		if err != nil {
			break
		}
		switch p.Header.(type) {
		case *mail.InlineHeader:
			ct := p.Header.Get("Content-Type")
			if strings.Contains(ct, "text/plain") || ct == "" {
				b, _ := io.ReadAll(p.Body)
				textBody = string(b)
			}
		}
	}
	return textBody
}

func readAll(r io.Reader) string {
	b, _ := io.ReadAll(r)
	return string(b)
}

func (w *Watcher) updateStatus(status string) {
	w.db.Model(&model.Account{}).Where("id = ?", w.account.ID).Update("status", status)
}
