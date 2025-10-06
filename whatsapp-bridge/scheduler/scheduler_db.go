package scheduler

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// ScheduledMessage represents a message scheduled to be sent in the future
type ScheduledMessage struct {
	ID              string    `json:"id"`
	Recipient       string    `json:"recipient"`
	Message         string    `json:"message"`
	ScheduledTime   time.Time `json:"scheduled_time"`
	CreatedAt       time.Time `json:"created_at"`
	LastMessageAt   time.Time `json:"last_message_at"`
	CheckForResponse bool     `json:"check_for_response"`
	Status          string    `json:"status"` // pending, sent, paused, cancelled, failed
	SentAt          *time.Time `json:"sent_at,omitempty"`
	ErrorMessage    *string   `json:"error_message,omitempty"`
}

// SchedulerDB handles database operations for scheduled messages
type SchedulerDB struct {
	db *sql.DB
}

// NewSchedulerDB creates a new scheduler database connection
func NewSchedulerDB(dbPath string) (*SchedulerDB, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open scheduler database: %w", err)
	}

	// Create table if not exists
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS scheduled_messages (
			id TEXT PRIMARY KEY,
			recipient TEXT NOT NULL,
			message TEXT NOT NULL,
			scheduled_time DATETIME NOT NULL,
			created_at DATETIME NOT NULL,
			last_message_at DATETIME,
			check_for_response BOOLEAN DEFAULT 1,
			status TEXT DEFAULT 'pending',
			sent_at DATETIME,
			error_message TEXT
		);

		CREATE INDEX IF NOT EXISTS idx_scheduled_time ON scheduled_messages(scheduled_time);
		CREATE INDEX IF NOT EXISTS idx_status ON scheduled_messages(status);
		CREATE INDEX IF NOT EXISTS idx_recipient ON scheduled_messages(recipient);
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to create scheduler table: %w", err)
	}

	return &SchedulerDB{db: db}, nil
}

// InsertScheduledMessage adds a new scheduled message to the database
func (sdb *SchedulerDB) InsertScheduledMessage(msg *ScheduledMessage) error {
	_, err := sdb.db.Exec(`
		INSERT INTO scheduled_messages 
		(id, recipient, message, scheduled_time, created_at, last_message_at, check_for_response, status)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`,
		msg.ID,
		msg.Recipient,
		msg.Message,
		msg.ScheduledTime,
		msg.CreatedAt,
		msg.LastMessageAt,
		msg.CheckForResponse,
		msg.Status,
	)
	return err
}

// GetPendingMessages retrieves messages that should be sent now
func (sdb *SchedulerDB) GetPendingMessages(now time.Time) ([]*ScheduledMessage, error) {
	rows, err := sdb.db.Query(`
		SELECT id, recipient, message, scheduled_time, created_at, last_message_at, 
		       check_for_response, status, sent_at, error_message
		FROM scheduled_messages
		WHERE status = 'pending' 
		  AND scheduled_time <= ?
		ORDER BY scheduled_time ASC
	`, now)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*ScheduledMessage
	for rows.Next() {
		msg := &ScheduledMessage{}
		var sentAt sql.NullTime
		var errorMsg sql.NullString
		var lastMessageAt sql.NullTime

		err := rows.Scan(
			&msg.ID,
			&msg.Recipient,
			&msg.Message,
			&msg.ScheduledTime,
			&msg.CreatedAt,
			&lastMessageAt,
			&msg.CheckForResponse,
			&msg.Status,
			&sentAt,
			&errorMsg,
		)
		if err != nil {
			return nil, err
		}

		if sentAt.Valid {
			msg.SentAt = &sentAt.Time
		}
		if errorMsg.Valid {
			msg.ErrorMessage = &errorMsg.String
		}
		if lastMessageAt.Valid {
			msg.LastMessageAt = lastMessageAt.Time
		}

		messages = append(messages, msg)
	}

	return messages, nil
}

// GetAllScheduledMessages retrieves all scheduled messages with optional filters
func (sdb *SchedulerDB) GetAllScheduledMessages(status string, recipient string) ([]*ScheduledMessage, error) {
	query := `
		SELECT id, recipient, message, scheduled_time, created_at, last_message_at,
		       check_for_response, status, sent_at, error_message
		FROM scheduled_messages
		WHERE 1=1
	`
	args := []interface{}{}

	if status != "" {
		query += " AND status = ?"
		args = append(args, status)
	}

	if recipient != "" {
		query += " AND recipient = ?"
		args = append(args, recipient)
	}

	query += " ORDER BY scheduled_time DESC"

	rows, err := sdb.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*ScheduledMessage
	for rows.Next() {
		msg := &ScheduledMessage{}
		var sentAt sql.NullTime
		var errorMsg sql.NullString
		var lastMessageAt sql.NullTime

		err := rows.Scan(
			&msg.ID,
			&msg.Recipient,
			&msg.Message,
			&msg.ScheduledTime,
			&msg.CreatedAt,
			&lastMessageAt,
			&msg.CheckForResponse,
			&msg.Status,
			&sentAt,
			&errorMsg,
		)
		if err != nil {
			return nil, err
		}

		if sentAt.Valid {
			msg.SentAt = &sentAt.Time
		}
		if errorMsg.Valid {
			msg.ErrorMessage = &errorMsg.String
		}
		if lastMessageAt.Valid {
			msg.LastMessageAt = lastMessageAt.Time
		}

		messages = append(messages, msg)
	}

	return messages, nil
}

// GetScheduledMessage retrieves a specific scheduled message by ID
func (sdb *SchedulerDB) GetScheduledMessage(id string) (*ScheduledMessage, error) {
	msg := &ScheduledMessage{}
	var sentAt sql.NullTime
	var errorMsg sql.NullString
	var lastMessageAt sql.NullTime

	err := sdb.db.QueryRow(`
		SELECT id, recipient, message, scheduled_time, created_at, last_message_at,
		       check_for_response, status, sent_at, error_message
		FROM scheduled_messages
		WHERE id = ?
	`, id).Scan(
		&msg.ID,
		&msg.Recipient,
		&msg.Message,
		&msg.ScheduledTime,
		&msg.CreatedAt,
		&lastMessageAt,
		&msg.CheckForResponse,
		&msg.Status,
		&sentAt,
		&errorMsg,
	)

	if err == sql.ErrNoRows {
		return nil, fmt.Errorf("scheduled message not found")
	}
	if err != nil {
		return nil, err
	}

	if sentAt.Valid {
		msg.SentAt = &sentAt.Time
	}
	if errorMsg.Valid {
		msg.ErrorMessage = &errorMsg.String
	}
	if lastMessageAt.Valid {
		msg.LastMessageAt = lastMessageAt.Time
	}

	return msg, nil
}

// UpdateMessageStatus updates the status of a scheduled message
func (sdb *SchedulerDB) UpdateMessageStatus(id string, status string, sentAt *time.Time, errorMsg *string) error {
	_, err := sdb.db.Exec(`
		UPDATE scheduled_messages
		SET status = ?, sent_at = ?, error_message = ?
		WHERE id = ?
	`, status, sentAt, errorMsg, id)
	return err
}

// DeleteScheduledMessage deletes a scheduled message
func (sdb *SchedulerDB) DeleteScheduledMessage(id string) error {
	_, err := sdb.db.Exec("DELETE FROM scheduled_messages WHERE id = ?", id)
	return err
}

// GetFutureMessagesForRecipient gets all future pending messages for a recipient
func (sdb *SchedulerDB) GetFutureMessagesForRecipient(recipient string, now time.Time) ([]*ScheduledMessage, error) {
	rows, err := sdb.db.Query(`
		SELECT id, recipient, message, scheduled_time, created_at, last_message_at,
		       check_for_response, status, sent_at, error_message
		FROM scheduled_messages
		WHERE recipient = ?
		  AND status = 'pending'
		  AND scheduled_time > ?
		  AND check_for_response = 1
		ORDER BY scheduled_time ASC
	`, recipient, now)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*ScheduledMessage
	for rows.Next() {
		msg := &ScheduledMessage{}
		var sentAt sql.NullTime
		var errorMsg sql.NullString
		var lastMessageAt sql.NullTime

		err := rows.Scan(
			&msg.ID,
			&msg.Recipient,
			&msg.Message,
			&msg.ScheduledTime,
			&msg.CreatedAt,
			&lastMessageAt,
			&msg.CheckForResponse,
			&msg.Status,
			&sentAt,
			&errorMsg,
		)
		if err != nil {
			return nil, err
		}

		if sentAt.Valid {
			msg.SentAt = &sentAt.Time
		}
		if errorMsg.Valid {
			msg.ErrorMessage = &errorMsg.String
		}
		if lastMessageAt.Valid {
			msg.LastMessageAt = lastMessageAt.Time
		}

		messages = append(messages, msg)
	}

	return messages, nil
}

// Close closes the database connection
func (sdb *SchedulerDB) Close() error {
	return sdb.db.Close()
}
