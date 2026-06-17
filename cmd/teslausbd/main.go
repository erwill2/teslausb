package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"teslausbd/internal/config"
	"teslausbd/internal/daemon"
)

func main() {
	// 1. Initialize configuration
	configPath := "/root/teslausb_setup_variables.conf"
	cfg, err := config.ParseConfig(configPath)
	if err != nil {
		if os.IsNotExist(err) {
			log.Printf("Config file %s not found, proceeding with defaults", configPath)
			cfg = &config.SystemConfig{} // default empty config
		} else {
			log.Fatalf("Failed to parse config: %v", err)
		}
	}

	log.Printf("Starting teslausbd. Configuration loaded. Archive Target: %s", cfg.ArchiveTarget)

	// 2. Setup Context with graceful termination signals
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigs
		log.Printf("Received signal %v. Initiating graceful shutdown...", sig)
		cancel()
	}()

	// 3. Initialize and run the daemon state machine
	d := daemon.NewDaemon()
	d.Run(ctx)

	log.Println("Daemon stopped cleanly.")
}
