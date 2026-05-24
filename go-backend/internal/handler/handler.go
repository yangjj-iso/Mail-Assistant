package handler

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"time"

	"mail-classifier/internal/classifier"
	imapMgr "mail-classifier/internal/imap"
	"mail-classifier/internal/model"
	"mail-classifier/internal/ws"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"gorm.io/gorm"
)

type Handler struct {
	DB         *gorm.DB
	Classifier *classifier.Client
	Hub        *ws.Hub
	EncKey     []byte
	ImapMgr    *imapMgr.Manager
}

func NewHandler(db *gorm.DB, cl *classifier.Client, hub *ws.Hub, encKey string) *Handler {
	key := []byte(encKey)
	if len(key) < 32 {
		padded := make([]byte, 32)
		copy(padded, key)
		key = padded
	}
	h := &Handler{DB: db, Classifier: cl, Hub: hub, EncKey: key[:32]}
	h.ImapMgr = imapMgr.NewManager(db, cl, hub, h.Decrypt)
	return h
}

func (h *Handler) RegisterRoutes(r *gin.Engine) {
	r.GET("/ws", h.handleWebSocket)

	api := r.Group("/api")
	api.POST("/accounts", h.createAccount)
	api.GET("/accounts", h.listAccounts)
	api.DELETE("/accounts/:id", h.deleteAccount)
	api.GET("/emails", h.listEmails)
	api.GET("/emails/:id", h.getEmail)
	api.GET("/stats", h.getStats)
	api.GET("/applications", h.listApplications)
	api.PATCH("/applications/:id", h.updateApplication)
	api.DELETE("/applications/:id", h.deleteApplication)
	api.GET("/applications/upcoming", h.upcomingInterviews)

	debug := api.Group("/debug")
	debug.POST("/email", h.debugInjectEmail)
}

func (h *Handler) createAccount(c *gin.Context) {
	var req struct {
		Email    string `json:"email" binding:"required"`
		IMAPHost string `json:"imap_host" binding:"required"`
		IMAPPort int    `json:"imap_port"`
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.IMAPPort == 0 {
		req.IMAPPort = 993
	}
	encrypted, err := h.encrypt(req.Password)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "encryption failed"})
		return
	}
	account := model.Account{
		Email:             req.Email,
		IMAPHost:          req.IMAPHost,
		IMAPPort:          req.IMAPPort,
		EncryptedPassword: encrypted,
		Status:            "disconnected",
	}
	if err := h.DB.Create(&account).Error; err != nil {
		c.JSON(http.StatusConflict, gin.H{"error": "account already exists"})
		return
	}

	h.ImapMgr.StartAccount(account)
	c.JSON(http.StatusCreated, account)
}

func (h *Handler) listAccounts(c *gin.Context) {
	var accounts []model.Account
	h.DB.Find(&accounts)
	c.JSON(http.StatusOK, accounts)
}

func (h *Handler) deleteAccount(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	h.ImapMgr.StopAccount(uint(id))
	if err := h.DB.Delete(&model.Account{}, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": id})
}

func (h *Handler) listEmails(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	size, _ := strconv.Atoi(c.DefaultQuery("size", "20"))
	label := c.Query("label")

	if page < 1 {
		page = 1
	}
	if size < 1 || size > 100 {
		size = 20
	}

	query := h.DB.Model(&model.Email{})
	if label != "" {
		query = query.Where("final_label = ?", label)
	}

	var total int64
	query.Count(&total)

	var emails []model.Email
	query.Order("date DESC").Offset((page - 1) * size).Limit(size).Find(&emails)

	c.JSON(http.StatusOK, gin.H{
		"items": emails,
		"total": total,
		"page":  page,
		"size":  size,
	})
}

func (h *Handler) getEmail(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var email model.Email
	if err := h.DB.First(&email, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	c.JSON(http.StatusOK, email)
}

func (h *Handler) getStats(c *gin.Context) {
	type LabelCount struct {
		FinalLabel string `json:"label"`
		Count      int64  `json:"count"`
	}
	var stats []LabelCount
	h.DB.Model(&model.Email{}).
		Select("final_label, count(*) as count").
		Group("final_label").
		Find(&stats)
	c.JSON(http.StatusOK, stats)
}

func (h *Handler) listApplications(c *gin.Context) {
	var apps []model.Application
	h.DB.Order("updated_at DESC").Find(&apps)

	grouped := make(map[string][]model.Application)
	for _, app := range apps {
		grouped[app.Stage] = append(grouped[app.Stage], app)
	}
	c.JSON(http.StatusOK, gin.H{
		"items":   apps,
		"grouped": grouped,
	})
}

func (h *Handler) updateApplication(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var app model.Application
	if err := h.DB.First(&app, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}

	var req struct {
		Stage    *string `json:"stage"`
		Notes    *string `json:"notes"`
		NextTime *string `json:"next_time"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Stage != nil {
		app.Stage = *req.Stage
	}
	if req.Notes != nil {
		app.Notes = *req.Notes
	}
	if req.NextTime != nil {
		if *req.NextTime == "" {
			app.NextTime = nil
		} else {
			t, err := time.Parse(time.RFC3339, *req.NextTime)
			if err == nil {
				app.NextTime = &t
			}
		}
	}

	h.DB.Save(&app)
	h.Hub.Broadcast(ws.Message{Type: "job_update", Data: app})
	c.JSON(http.StatusOK, app)
}

func (h *Handler) deleteApplication(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	if err := h.DB.Delete(&model.Application{}, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": id})
}

func (h *Handler) upcomingInterviews(c *gin.Context) {
	var apps []model.Application
	h.DB.Where("next_time IS NOT NULL AND next_time > ?", time.Now().Add(-24*time.Hour)).
		Order("next_time ASC").
		Limit(20).
		Find(&apps)
	c.JSON(http.StatusOK, apps)
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

func (h *Handler) handleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		return
	}
	h.Hub.Register(conn)
	defer h.Hub.Unregister(conn)
	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			break
		}
	}
}

func (h *Handler) debugInjectEmail(c *gin.Context) {
	var req struct {
		Subject  string `json:"subject"`
		From     string `json:"from"`
		Body     string `json:"body"`
		Date     string `json:"date"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Subject == "" && req.Body == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "subject or body required"})
		return
	}
	if req.From == "" {
		req.From = "debug@localhost"
	}

	date := time.Now()
	if req.Date != "" {
		if t, err := time.Parse(time.RFC3339, req.Date); err == nil {
			date = t
		}
	}

	messageID := "debug-" + strconv.FormatInt(time.Now().UnixNano(), 36)
	text := req.Subject + " " + req.Body

	// Stage 1+2 classification
	result, err := h.Classifier.Predict(text)
	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "classifier unavailable: " + err.Error()})
		return
	}

	preview := req.Body
	if len(preview) > 200 {
		preview = preview[:200]
	}

	finalLabel := result.Stage1Label
	if result.Stage2Label != nil && *result.Stage2Label != "" {
		finalLabel = *result.Stage2Label
	}

	email := model.Email{
		AccountID:    0,
		MessageID:    messageID,
		Subject:      req.Subject,
		FromAddr:     req.From,
		Date:         date,
		BodyPreview:  preview,
		Stage1Label:  result.Stage1Label,
		Stage2Label:  result.Stage2Label,
		FinalLabel:   finalLabel,
		ClassifiedAt: time.Now(),
	}

	// Job classification
	jobResult, _ := h.Classifier.PredictJob(req.Body, req.Subject)
	if jobResult != nil && jobResult.IsJob {
		email.IsJob = true
		email.JobStage = jobResult.Stage
		entJSON, _ := json.Marshal(jobResult.Entities)
		email.Entities = string(entJSON)
	}

	if err := h.DB.Create(&email).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "db save failed"})
		return
	}

	// Upsert application if job email
	var app *model.Application
	if email.IsJob && jobResult != nil {
		app = h.upsertApplicationFromDebug(&email, jobResult)
	}

	h.Hub.Broadcast(ws.Message{Type: "new_email", Data: email})

	resp := gin.H{
		"email":          email,
		"classification": result,
		"job":            jobResult,
	}
	if app != nil {
		resp["application"] = app
	}
	c.JSON(http.StatusOK, resp)
}

func (h *Handler) upsertApplicationFromDebug(email *model.Email, jobResult *classifier.JobPredictResponse) *model.Application {
	company := ""
	position := ""
	if len(jobResult.Entities.Company) > 0 {
		company = jobResult.Entities.Company[0]
	}
	if len(jobResult.Entities.Position) > 0 {
		position = jobResult.Entities.Position[0]
	}
	if company == "" && position == "" {
		return nil
	}

	var app model.Application
	query := h.DB.Where("1 = 1")
	if company != "" {
		query = query.Where("company = ?", company)
	}
	if position != "" {
		query = query.Where("position = ?", position)
	}

	err := query.First(&app).Error
	if err == gorm.ErrRecordNotFound {
		app = model.Application{
			AccountID:   0,
			Company:     company,
			Position:    position,
			Stage:       jobResult.Stage,
			LastEmailID: email.ID,
		}
		if len(jobResult.Entities.Round) > 0 {
			app.NextRound = jobResult.Entities.Round[0]
		}
		if len(jobResult.Entities.Location) > 0 {
			app.Location = jobResult.Entities.Location[0]
		}
		h.DB.Create(&app)
	} else if err == nil {
		app.Stage = jobResult.Stage
		app.LastEmailID = email.ID
		if len(jobResult.Entities.Location) > 0 {
			app.Location = jobResult.Entities.Location[0]
		}
		if len(jobResult.Entities.Round) > 0 {
			app.NextRound = jobResult.Entities.Round[0]
		}
		h.DB.Save(&app)
	}

	if app.ID > 0 {
		appID := app.ID
		email.ApplicationID = &appID
		h.DB.Save(email)
		h.Hub.Broadcast(ws.Message{Type: "job_update", Data: app})
	}
	return &app
}

func (h *Handler) encrypt(plaintext string) (string, error) {
	block, err := aes.NewCipher(h.EncKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}
	ciphertext := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func (h *Handler) Decrypt(encrypted string) (string, error) {
	data, err := base64.StdEncoding.DecodeString(encrypted)
	if err != nil {
		return "", err
	}
	block, err := aes.NewCipher(h.EncKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return "", io.ErrUnexpectedEOF
	}
	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}
	return string(plaintext), nil
}
