package scheduler

import (
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// ScheduleMessageRequest represents the request to schedule a message
type ScheduleMessageRequest struct {
	Recipient        string `json:"recipient"`
	Message          string `json:"message"`
	ScheduledTime    string `json:"scheduled_time"` // ISO-8601 format
	CheckForResponse bool   `json:"check_for_response"`
}

// SetupHandlers registers HTTP handlers for scheduler endpoints
func SetupHandlers(scheduler *MessageScheduler) {
	// POST /api/schedule - Schedule a new message
	http.HandleFunc("/api/schedule", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req ScheduleMessageRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		// Validate required fields
		if req.Recipient == "" {
			http.Error(w, "Recipient is required", http.StatusBadRequest)
			return
		}
		if req.Message == "" {
			http.Error(w, "Message is required", http.StatusBadRequest)
			return
		}
		if req.ScheduledTime == "" {
			http.Error(w, "Scheduled time is required", http.StatusBadRequest)
			return
		}

		// Parse scheduled time
		scheduledTime, err := time.Parse(time.RFC3339, req.ScheduledTime)
		if err != nil {
			http.Error(w, "Invalid scheduled_time format. Use ISO-8601 (e.g., 2025-10-06T15:30:00Z)", http.StatusBadRequest)
			return
		}

		// Schedule the message
		scheduledMsg, err := scheduler.ScheduleMessage(
			req.Recipient,
			req.Message,
			scheduledTime,
			req.CheckForResponse,
		)
		if err != nil {
			log.Printf("Error scheduling message: %v", err)
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success":          true,
			"message":          "Message scheduled successfully",
			"scheduled_message": scheduledMsg,
		})
	})

	// GET /api/scheduled - List all scheduled messages
	http.HandleFunc("/api/scheduled", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Get query parameters
		status := r.URL.Query().Get("status")
		recipient := r.URL.Query().Get("recipient")

		messages, err := scheduler.schedulerDB.GetAllScheduledMessages(status, recipient)
		if err != nil {
			log.Printf("Error getting scheduled messages: %v", err)
			http.Error(w, "Failed to get scheduled messages", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success":  true,
			"messages": messages,
		})
	})

	// GET /api/scheduled/{id} - Get a specific scheduled message
	http.HandleFunc("/api/scheduled/", func(w http.ResponseWriter, r *http.Request) {
		// Extract ID from path
		id := r.URL.Path[len("/api/scheduled/"):]
		if id == "" {
			http.Error(w, "Message ID is required", http.StatusBadRequest)
			return
		}

		switch r.Method {
		case http.MethodGet:
			// Get specific message
			msg, err := scheduler.schedulerDB.GetScheduledMessage(id)
			if err != nil {
				log.Printf("Error getting scheduled message: %v", err)
				http.Error(w, "Message not found", http.StatusNotFound)
				return
			}

			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"message": msg,
			})

		case http.MethodDelete:
			// Delete (cancel) scheduled message
			// First check if message exists and is still pending
			msg, err := scheduler.schedulerDB.GetScheduledMessage(id)
			if err != nil {
				http.Error(w, "Message not found", http.StatusNotFound)
				return
			}

			if msg.Status != "pending" && msg.Status != "paused" {
				http.Error(w, "Can only cancel pending or paused messages", http.StatusBadRequest)
				return
			}

			// Update status to cancelled
			if err := scheduler.schedulerDB.UpdateMessageStatus(id, "cancelled", nil, stringPtr("Cancelled by user")); err != nil {
				log.Printf("Error cancelling message: %v", err)
				http.Error(w, "Failed to cancel message", http.StatusInternalServerError)
				return
			}

			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"message": "Message cancelled successfully",
			})

		case http.MethodPatch:
			// Pause or resume scheduled message
			var req struct {
				Action string `json:"action"` // "pause" or "resume"
			}
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				http.Error(w, "Invalid request body", http.StatusBadRequest)
				return
			}

			msg, err := scheduler.schedulerDB.GetScheduledMessage(id)
			if err != nil {
				http.Error(w, "Message not found", http.StatusNotFound)
				return
			}

			var newStatus string
			var reason *string

			switch req.Action {
			case "pause":
				if msg.Status != "pending" {
					http.Error(w, "Can only pause pending messages", http.StatusBadRequest)
					return
				}
				newStatus = "paused"
				reason = stringPtr("Paused by user")

			case "resume":
				if msg.Status != "paused" {
					http.Error(w, "Can only resume paused messages", http.StatusBadRequest)
					return
				}
				newStatus = "pending"
				reason = nil

			default:
				http.Error(w, "Invalid action. Use 'pause' or 'resume'", http.StatusBadRequest)
				return
			}

			if err := scheduler.schedulerDB.UpdateMessageStatus(id, newStatus, nil, reason); err != nil {
				log.Printf("Error updating message status: %v", err)
				http.Error(w, "Failed to update message", http.StatusInternalServerError)
				return
			}

			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"message": "Message " + req.Action + "d successfully",
			})

		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
}
