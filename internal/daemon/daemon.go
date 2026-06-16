package daemon

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"
)

type State string

const (
	StateIdle            State = "IDLE"
	StateCheckingNetwork State = "CHECKING_NETWORK"
	StateRecording       State = "RECORDING"
	StateArchiving       State = "ARCHIVING"
	StateRepair          State = "REPAIR"
)

type LogEntry struct {
	Time         string `json:"time"`
	Level        string `json:"level"`
	CurrentState string `json:"current_state"`
	Message      string `json:"message"`
}

type Daemon struct {
	currentState State
	logger       *log.Logger
	// dependencies like gadget, network checker, storage would be injected here
}

func NewDaemon() *Daemon {
	return &Daemon{
		currentState: StateIdle,
		logger:       log.New(os.Stdout, "", 0), // custom formatting handled by json log
	}
}

func (d *Daemon) logMsg(level, message string) {
	entry := LogEntry{
		Time:         time.Now().Format(time.RFC3339),
		Level:        level,
		CurrentState: string(d.currentState),
		Message:      message,
	}
	b, _ := json.Marshal(entry)
	d.logger.Println(string(b))
}

func (d *Daemon) Info(message string) {
	d.logMsg("INFO", message)
}

func (d *Daemon) Error(message string) {
	d.logMsg("ERROR", message)
}

// SetState updates the state.
func (d *Daemon) SetState(newState State) {
	d.Info(fmt.Sprintf("State transition: %s -> %s", d.currentState, newState))
	d.currentState = newState
}

// Run starts the daemon loop.
func (d *Daemon) Run(ctx context.Context) {
	d.Info("Daemon starting")

	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	// Initial evaluation
	d.evaluateState()

	for {
		select {
		case <-ctx.Done():
			d.Info("Daemon stopping due to context cancellation")
			return
		case <-ticker.C:
			d.evaluateState()
		}
	}
}

// evaluateState processes the logic for the current state.
func (d *Daemon) evaluateState() {
	d.Info("Evaluating state logic")
	switch d.currentState {
	case StateIdle:
		d.Info("Checking hardware registers and config integrity")
		// Assume initialization is done, transition to network check
		d.SetState(StateCheckingNetwork)

	case StateCheckingNetwork:
		d.Info("Checking Wi-Fi connectivity via netlink")
		// Mock logic: randomly transition to recording or archiving based on a condition
		// In a real implementation this checks the network interface natively.
		wifiFound := checkWiFi()
		if wifiFound {
			d.SetState(StateArchiving)
		} else {
			d.SetState(StateRecording)
		}

	case StateRecording:
		d.Info("Exposing USB gadget to vehicle")
		// Logic to detach from internal loop, attach ConfigFS gadget to host
		// If an error is detected or an unclean shutdown happens, transition to REPAIR

	case StateArchiving:
		d.Info("Syncing footage to archive")
		// Logic to unmount gadget, mount internally, trigger sync
		// Transition to IDLE or REPAIR on completion/error

	case StateRepair:
		d.Info("Running native fsck pipeline")
		// On success: return to IDLE
		d.SetState(StateIdle)
	}
}

// Mock wifi check
func checkWiFi() bool {
	// Dummy implementation, replace with netlink call
	return false
}
