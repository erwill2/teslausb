package gadget

import (
	"fmt"
	"os"
	"path/filepath"
)

const configFsBase = "/sys/kernel/config/usb_gadget/teslausb"

// WriteStringToFile writes a string to a file safely.
func WriteStringToFile(path, content string) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_TRUNC|os.O_CREATE, 0644)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", path, err)
	}
	defer f.Close()

	_, err = f.WriteString(content)
	if err != nil {
		return fmt.Errorf("failed to write to %s: %w", path, err)
	}

	return nil
}

// SetupGadget configures the USB mass storage gadget via ConfigFS.
func SetupGadget(backingFilePath string, vendorID string, productID string, serialNumber string) error {
	// Create main gadget directory
	if err := os.MkdirAll(configFsBase, 0755); err != nil {
		return fmt.Errorf("failed to create configfs dir %s: %w", configFsBase, err)
	}

	// Write IDs
	if err := WriteStringToFile(filepath.Join(configFsBase, "idVendor"), vendorID); err != nil {
		return err
	}
	if err := WriteStringToFile(filepath.Join(configFsBase, "idProduct"), productID); err != nil {
		return err
	}

	// Setup English strings
	stringsDir := filepath.Join(configFsBase, "strings/0x409")
	if err := os.MkdirAll(stringsDir, 0755); err != nil {
		return fmt.Errorf("failed to create strings dir: %w", err)
	}

	if err := WriteStringToFile(filepath.Join(stringsDir, "serialnumber"), serialNumber); err != nil {
		return err
	}
	if err := WriteStringToFile(filepath.Join(stringsDir, "manufacturer"), "TeslaUSB"); err != nil {
		return err
	}
	if err := WriteStringToFile(filepath.Join(stringsDir, "product"), "TeslaUSB Mass Storage"); err != nil {
		return err
	}

	// Create mass storage function
	funcDir := filepath.Join(configFsBase, "functions/mass_storage.usb0")
	if err := os.MkdirAll(funcDir, 0755); err != nil {
		return fmt.Errorf("failed to create mass storage function: %w", err)
	}

	// Write backing file path to LUN 0
	lunDir := filepath.Join(funcDir, "lun.0")
	if err := os.MkdirAll(lunDir, 0755); err != nil { // Ensure LUN dir exists (though usually created by function module)
		// It might already exist or be handled by module
	}
	if err := WriteStringToFile(filepath.Join(lunDir, "file"), backingFilePath); err != nil {
		return err
	}

	// Create config
	cfgDir := filepath.Join(configFsBase, "configs/c.1")
	if err := os.MkdirAll(cfgDir, 0755); err != nil {
		return fmt.Errorf("failed to create config dir: %w", err)
	}

	// Link function to config
	funcLink := filepath.Join(cfgDir, "mass_storage.usb0")
	if _, err := os.Stat(funcLink); os.IsNotExist(err) {
		if err := os.Symlink(funcDir, funcLink); err != nil {
			return fmt.Errorf("failed to link mass storage function to config: %w", err)
		}
	}

	return nil
}

// EnableGadget links the gadget to the UDC controller to enable it.
func EnableGadget(udcName string) error {
	udcFile := filepath.Join(configFsBase, "UDC")
	return WriteStringToFile(udcFile, udcName)
}

// DisableGadget writes an empty string to UDC to disable it.
func DisableGadget() error {
	udcFile := filepath.Join(configFsBase, "UDC")
	return WriteStringToFile(udcFile, "")
}

// GetUDCName attempts to find an active UDC.
func GetUDCName() (string, error) {
	udcClassDir := "/sys/class/udc"
	entries, err := os.ReadDir(udcClassDir)
	if err != nil {
		return "", fmt.Errorf("failed to read %s: %w", udcClassDir, err)
	}
	for _, entry := range entries {
		if entry.IsDir() || entry.Type()&os.ModeSymlink != 0 {
			return entry.Name(), nil
		}
	}
	return "", fmt.Errorf("no UDC found in %s", udcClassDir)
}
