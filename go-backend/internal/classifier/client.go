package classifier

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type PredictRequest struct {
	Text string `json:"text"`
	Mode string `json:"mode"`
}

type PredictResponse struct {
	Stage1Label              string  `json:"stage1_label"`
	Stage1Index              int     `json:"stage1_index"`
	Final                    string  `json:"final"`
	Stage2Label              *string `json:"stage2_label"`
	Stage2Index              *int    `json:"stage2_index"`
	EffectiveFusionWStage1   float64 `json:"effective_fusion_weight_stage1"`
	EffectiveFusionWStage2   float64 `json:"effective_fusion_weight_stage2"`
}

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) Predict(text string) (*PredictResponse, error) {
	reqBody := PredictRequest{Text: text, Mode: "soft"}
	data, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	resp, err := c.httpClient.Post(
		c.baseURL+"/v1/predict",
		"application/json",
		bytes.NewReader(data),
	)
	if err != nil {
		return nil, fmt.Errorf("post predict: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("predict returned %d: %s", resp.StatusCode, string(body))
	}

	var result PredictResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &result, nil
}

func (c *Client) Health() error {
	resp, err := c.httpClient.Get(c.baseURL + "/v1/health")
	if err != nil {
		return fmt.Errorf("health check: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health returned %d", resp.StatusCode)
	}
	return nil
}

type JobPredictRequest struct {
	Text    string `json:"text"`
	Subject string `json:"subject"`
}

type EntityResult struct {
	Company  []string `json:"company"`
	Position []string `json:"position"`
	Time     []string `json:"time"`
	Round    []string `json:"round"`
	Location []string `json:"location"`
}

type JobPredictResponse struct {
	IsJob           bool         `json:"is_job"`
	Confidence      float64      `json:"confidence"`
	Stage           string       `json:"stage,omitempty"`
	StageConfidence float64      `json:"stage_confidence,omitempty"`
	Entities        EntityResult `json:"entities"`
}

func (c *Client) PredictJob(text, subject string) (*JobPredictResponse, error) {
	reqBody := JobPredictRequest{Text: text, Subject: subject}
	data, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal job request: %w", err)
	}

	resp, err := c.httpClient.Post(
		c.baseURL+"/v1/job/predict",
		"application/json",
		bytes.NewReader(data),
	)
	if err != nil {
		return nil, fmt.Errorf("post job predict: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusServiceUnavailable {
		return nil, nil
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("job predict returned %d: %s", resp.StatusCode, string(body))
	}

	var result JobPredictResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode job response: %w", err)
	}
	return &result, nil
}
