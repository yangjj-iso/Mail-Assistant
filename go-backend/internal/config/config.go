package config

import "os"

type Config struct {
	Port          string
	MLServiceURL  string
	DBPath        string
	EncryptionKey string
}

func Load() *Config {
	return &Config{
		Port:          getEnv("PORT", "8080"),
		MLServiceURL:  getEnv("ML_SERVICE_URL", "http://127.0.0.1:8081"),
		DBPath:        getEnv("DB_PATH", "data.db"),
		EncryptionKey: getEnv("ENCRYPTION_KEY", "mail-classifier-secret-key-32b!"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
