package scheduler

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"go.mau.fi/whatsmeow"
)

// MessageSender is a function type for sending WhatsApp messages
type MessageSender func(client *whatsmeow.Client, recipient string, message string, mediaPath string) (bool, string)

// MessageScheduler handles the scheduling and sending of messages
type MessageScheduler struct {
	schedulerDB   *SchedulerDB
	whatsappDB    *sql.DB
	client        *whatsmeow.Client
	ticker        *time.Ticker
	stopChan      chan bool
	messageSender MessageSender
}

// NewMessageScheduler creates a new message scheduler
func NewMessageScheduler(schedulerDB *SchedulerDB, whatsappDB *sql.DB, client *whatsmeow.Client, messageSender MessageSender) *MessageScheduler {
	return &MessageScheduler{
		schedulerDB:   schedulerDB,
		whatsappDB:    whatsappDB,
		client:        client,
		stopChan:      make(chan bool),
		messageSender: messageSender,
	}
}

// Start begins the scheduler background worker
func (ms *MessageScheduler) Start(checkInterval time.Duration) {
	log.Println("📅 Starting message scheduler worker...")
	ms.ticker = time.NewTicker(checkInterval)

	go func() {
		for {
			select {
			case <-ms.ticker.C:
				ms.processScheduledMessages()
			case <-ms.stopChan:
				log.Println("📅 Stopping message scheduler worker...")
				return
			}
		}
	}()
}

// Stop stops the scheduler
func (ms *MessageScheduler) Stop() {
	if ms.ticker != nil {
		ms.ticker.Stop()
	}
	ms.stopChan <- true
}

// processScheduledMessages checks and sends messages that are due
func (ms *MessageScheduler) processScheduledMessages() {
	now := time.Now()

	// Step 1: Check for future messages that should be paused due to responses
	if err := ms.checkAndPauseFutureMessages(now); err != nil {
		log.Printf("⚠️ Error checking future messages: %v", err)
	}

	// Step 2: Get pending messages that should be sent now
	messages, err := ms.schedulerDB.GetPendingMessages(now)
	if err != nil {
		log.Printf("❌ Error getting pending messages: %v", err)
		return
	}

	if len(messages) == 0 {
		return
	}

	log.Printf("📬 Processing %d scheduled messages...", len(messages))

	for _, msg := range messages {
		if err := ms.processSingleMessage(msg); err != nil {
			log.Printf("❌ Error processing message %s: %v", msg.ID, err)
		}
	}
}

// checkAndPauseFutureMessages checks if any future pending messages should be paused
func (ms *MessageScheduler) checkAndPauseFutureMessages(now time.Time) error {
	// Get all pending messages with check_for_response = true
	allPending, err := ms.schedulerDB.GetAllScheduledMessages("pending", "")
	if err != nil {
		return err
	}

	for _, msg := range allPending {
		if !msg.CheckForResponse {
			continue
		}

		// Check if recipient has sent a message after the scheduled message was created
		hasNewMessage, err := ms.hasRecipientResponded(msg.Recipient, msg.CreatedAt)
		if err != nil {
			log.Printf("⚠️ Error checking response for %s: %v", msg.ID, err)
			continue
		}

		if hasNewMessage {
			// Pause the message
			log.Printf("⏸️ Pausing message %s - recipient %s has responded", msg.ID, msg.Recipient)
			if err := ms.schedulerDB.UpdateMessageStatus(msg.ID, "paused", nil, stringPtr("Recipient responded before scheduled time")); err != nil {
				log.Printf("❌ Error pausing message %s: %v", msg.ID, err)
			}
		}
	}

	return nil
}

// processSingleMessage processes and sends a single scheduled message
func (ms *MessageScheduler) processSingleMessage(msg *ScheduledMessage) error {
	// Check if we should send the message (verify condition)
	shouldSend := true

	if msg.CheckForResponse {
		hasResponded, err := ms.hasRecipientResponded(msg.Recipient, msg.CreatedAt)
		if err != nil {
			errMsg := fmt.Sprintf("Error checking recipient response: %v", err)
			ms.schedulerDB.UpdateMessageStatus(msg.ID, "failed", nil, &errMsg)
			return err
		}

		if hasResponded {
			// Don't send - recipient has responded
			shouldSend = false
			log.Printf("⏸️ Pausing message %s - recipient %s has responded", msg.ID, msg.Recipient)
			return ms.schedulerDB.UpdateMessageStatus(msg.ID, "paused", nil, stringPtr("Recipient responded before scheduled time"))
		}
	}

	if !shouldSend {
		return nil
	}

	// Send the message
	log.Printf("📤 Sending scheduled message %s to %s", msg.ID, msg.Recipient)
	
	success, errMsg := ms.messageSender(ms.client, msg.Recipient, msg.Message, "")
	if !success {
		ms.schedulerDB.UpdateMessageStatus(msg.ID, "failed", nil, &errMsg)
		return fmt.Errorf("failed to send message: %s", errMsg)
	}

	// Mark as sent
	now := time.Now()
	if err := ms.schedulerDB.UpdateMessageStatus(msg.ID, "sent", &now, nil); err != nil {
		return err
	}

	log.Printf("✅ Successfully sent scheduled message %s to %s", msg.ID, msg.Recipient)
	return nil
}

// hasRecipientResponded checks if the recipient has sent a message after the given time
func (ms *MessageScheduler) hasRecipientResponded(recipient string, afterTime time.Time) (bool, error) {
	// Normalize recipient to JID format if needed
	recipientJID := recipient
	if !contains(recipient, "@") {
		recipientJID = recipient + "@s.whatsapp.net"
	}

	// Query the messages table for any message from this recipient after the given time
	var count int
	err := ms.whatsappDB.QueryRow(`
		SELECT COUNT(*)
		FROM messages
		WHERE sender = ?
		  AND is_from_me = 0
		  AND timestamp > ?
		LIMIT 1
	`, recipientJID, afterTime.Format(time.RFC3339)).Scan(&count)

	if err != nil {
		return false, err
	}

	return count > 0, nil
}

// ScheduleMessage creates a new scheduled message
func (ms *MessageScheduler) ScheduleMessage(recipient string, message string, scheduledTime time.Time, checkForResponse bool) (*ScheduledMessage, error) {
	// Validate scheduled time is in the future
	if scheduledTime.Before(time.Now()) {
		return nil, fmt.Errorf("scheduled time must be in the future")
	}

	// Normalize recipient to JID format if needed
	recipientJID := recipient
	if !contains(recipient, "@") {
		recipientJID = recipient + "@s.whatsapp.net"
	}

	// Get last message time from recipient
	lastMessageAt, err := ms.getLastMessageTime(recipientJID)
	if err != nil {
		log.Printf("⚠️ Could not get last message time for %s: %v", recipientJID, err)
		// Continue anyway with zero time
		lastMessageAt = time.Time{}
	}

	// Create scheduled message
	scheduledMsg := &ScheduledMessage{
		ID:               uuid.New().String(),
		Recipient:        recipientJID,
		Message:          message,
		ScheduledTime:    scheduledTime,
		CreatedAt:        time.Now(),
		LastMessageAt:    lastMessageAt,
		CheckForResponse: checkForResponse,
		Status:           "pending",
	}

	// Insert into database
	if err := ms.schedulerDB.InsertScheduledMessage(scheduledMsg); err != nil {
		return nil, fmt.Errorf("failed to insert scheduled message: %w", err)
	}

	log.Printf("✅ Scheduled message %s for %s at %s", scheduledMsg.ID, recipient, scheduledTime.Format(time.RFC3339))
	return scheduledMsg, nil
}

// getLastMessageTime gets the timestamp of the last message received from a recipient
func (ms *MessageScheduler) getLastMessageTime(recipient string) (time.Time, error) {
	var timestamp string
	err := ms.whatsappDB.QueryRow(`
		SELECT timestamp
		FROM messages
		WHERE sender = ?
		  AND is_from_me = 0
		ORDER BY timestamp DESC
		LIMIT 1
	`, recipient).Scan(&timestamp)

	if err == sql.ErrNoRows {
		return time.Time{}, nil // No messages found
	}
	if err != nil {
		return time.Time{}, err
	}

	return time.Parse(time.RFC3339, timestamp)
}

// Helper functions

func stringPtr(s string) *string {
	return &s
}

func contains(s string, substr string) bool {
	return len(s) > 0 && len(substr) > 0 && s != "" && substr != "" && 
		   (s == substr || (len(s) > len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr || containsMiddle(s, substr))))
}

func containsMiddle(s string, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
