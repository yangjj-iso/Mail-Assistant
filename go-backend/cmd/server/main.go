package main

import (
	"log"

	"mail-classifier/internal/classifier"
	"mail-classifier/internal/config"
	"mail-classifier/internal/handler"
	"mail-classifier/internal/model"
	"mail-classifier/internal/ws"

	"github.com/gin-gonic/gin"
)

func main() {
	cfg := config.Load()

	db, err := model.InitDB(cfg.DBPath)
	if err != nil {
		log.Fatalf("failed to init db: %v", err)
	}

	cl := classifier.NewClient(cfg.MLServiceURL)
	hub := ws.NewHub()
	h := handler.NewHandler(db, cl, hub, cfg.EncryptionKey)

	h.ImapMgr.StartAll()

	r := gin.Default()
	r.Use(corsMiddleware())
	h.RegisterRoutes(r)

	log.Printf("Go backend starting on :%s", cfg.Port)
	log.Printf("ML service: %s", cfg.MLServiceURL)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	}
}
