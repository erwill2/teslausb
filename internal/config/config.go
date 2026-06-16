package config

import (
	"bufio"
	"os"
	"strings"
)

type SystemConfig struct {
	ArchiveSystem string // cifs, rsync, rclone, local
	CifsUsername  string
	CifsPassword  string
	ArchiveTarget string
	DriveSize     string
	BleEnabled    bool
}

// ParseConfig reads a file and parses it into SystemConfig.
func ParseConfig(filepath string) (*SystemConfig, error) {
	file, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	return Parse(file)
}

// Parse parses the content of the configuration file.
func Parse(r *os.File) (*SystemConfig, error) {
	var config SystemConfig

	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Ignore empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Strip export prefix
		if strings.HasPrefix(line, "export ") {
			line = strings.TrimPrefix(line, "export ")
			line = strings.TrimSpace(line)
		}

		// Split by equal sign
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])

		// Handle quotes
		if (strings.HasPrefix(value, "\"") && strings.HasSuffix(value, "\"")) ||
			(strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'")) {
			value = value[1 : len(value)-1]
		}

		switch key {
		case "ARCHIVE_SYSTEM":
			config.ArchiveSystem = value
		case "CIFS_USERNAME":
			config.CifsUsername = value
		case "CIFS_PASSWORD":
			config.CifsPassword = value
		case "ARCHIVE_TARGET":
			config.ArchiveTarget = value
		case "DRIVE_SIZE":
			config.DriveSize = value
		case "BLE_ENABLED":
			if strings.ToLower(value) == "true" || value == "1" {
				config.BleEnabled = true
			} else {
				config.BleEnabled = false
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return &config, nil
}

// ParseString is a helper for unit testing.
func ParseString(content string) (*SystemConfig, error) {
	var config SystemConfig

	scanner := bufio.NewScanner(strings.NewReader(content))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Ignore empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// Strip export prefix
		if strings.HasPrefix(line, "export ") {
			line = strings.TrimPrefix(line, "export ")
			line = strings.TrimSpace(line)
		}

		// Split by equal sign
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])

		// Handle quotes
		if (strings.HasPrefix(value, "\"") && strings.HasSuffix(value, "\"")) ||
			(strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'")) {
			value = value[1 : len(value)-1]
		}

		switch key {
		case "ARCHIVE_SYSTEM":
			config.ArchiveSystem = value
		case "CIFS_USERNAME":
			config.CifsUsername = value
		case "CIFS_PASSWORD":
			config.CifsPassword = value
		case "ARCHIVE_TARGET":
			config.ArchiveTarget = value
		case "DRIVE_SIZE":
			config.DriveSize = value
		case "BLE_ENABLED":
			if strings.ToLower(value) == "true" || value == "1" {
				config.BleEnabled = true
			} else {
				config.BleEnabled = false
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return &config, nil
}
