package storage

import (
	"crypto/sha256"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"syscall"
)

// CheckFilesystem health via low-level fsck.vfat block check.
func CheckFilesystem(targetFile string) (int, error) {
	cmd := exec.Command("fsck.vfat", "-a", targetFile)
	err := cmd.Run()

	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			status := exitError.Sys().(syscall.WaitStatus)
			return status.ExitStatus(), nil
		}
		return -1, fmt.Errorf("failed to run fsck: %w", err)
	}

	return 0, nil // Success
}

// CopyTask represents a file copy job.
type CopyTask struct {
	Source      string
	Destination string
}

// CopyResult represents the result of a copy job.
type CopyResult struct {
	Task     CopyTask
	Checksum string
	Error    error
}

// SyncFiles starts an asynchronous file copy pipeline utilizing worker pools.
func SyncFiles(tasks []CopyTask, numWorkers int) []CopyResult {
	taskCh := make(chan CopyTask, len(tasks))
	resultCh := make(chan CopyResult, len(tasks))

	var wg sync.WaitGroup

	// Start workers
	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for task := range taskCh {
				checksum, err := copyWithChecksum(task.Source, task.Destination)
				resultCh <- CopyResult{
					Task:     task,
					Checksum: checksum,
					Error:    err,
				}
			}
		}()
	}

	// Send tasks
	for _, task := range tasks {
		taskCh <- task
	}
	close(taskCh)

	// Wait for completion in background and close results
	go func() {
		wg.Wait()
		close(resultCh)
	}()

	// Collect results
	var results []CopyResult
	for result := range resultCh {
		results = append(results, result)
	}

	return results
}

// copyWithChecksum streams reads to write directly and calculates SHA-256 on the fly.
func copyWithChecksum(src, dst string) (string, error) {
	srcFile, err := os.Open(src)
	if err != nil {
		return "", fmt.Errorf("failed to open source %s: %w", src, err)
	}
	defer srcFile.Close()

	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		return "", fmt.Errorf("failed to create dest dir %s: %w", filepath.Dir(dst), err)
	}

	dstFile, err := os.Create(dst)
	if err != nil {
		return "", fmt.Errorf("failed to create destination %s: %w", dst, err)
	}
	defer dstFile.Close()

	hash := sha256.New()

	// MultiWriter writes to both the destination file and the SHA256 hasher concurrently
	writer := io.MultiWriter(dstFile, hash)

	if _, err := io.Copy(writer, srcFile); err != nil {
		return "", fmt.Errorf("failed to copy data from %s to %s: %w", src, dst, err)
	}

	checksum := fmt.Sprintf("%x", hash.Sum(nil))
	return checksum, nil
}
