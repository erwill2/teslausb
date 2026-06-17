package config

import (
	"reflect"
	"testing"
)

func TestParseString(t *testing.T) {
	tests := []struct {
		name    string
		content string
		want    *SystemConfig
		wantErr bool
	}{
		{
			name: "Basic standard config",
			content: `
ARCHIVE_SYSTEM=cifs
CIFS_USERNAME=testuser
CIFS_PASSWORD=testpass
ARCHIVE_TARGET=//server/share
DRIVE_SIZE=64G
BLE_ENABLED=true
`,
			want: &SystemConfig{
				ArchiveSystem: "cifs",
				CifsUsername:  "testuser",
				CifsPassword:  "testpass",
				ArchiveTarget: "//server/share",
				DriveSize:     "64G",
				BleEnabled:    true,
			},
			wantErr: false,
		},
		{
			name: "With export prefixes and comments",
			content: `
# This is a comment
export ARCHIVE_SYSTEM="rsync"
export CIFS_USERNAME='otheruser'
export CIFS_PASSWORD="password123"
export ARCHIVE_TARGET="/mnt/archive"
export DRIVE_SIZE=128G
export BLE_ENABLED=0
`,
			want: &SystemConfig{
				ArchiveSystem: "rsync",
				CifsUsername:  "otheruser",
				CifsPassword:  "password123",
				ArchiveTarget: "/mnt/archive",
				DriveSize:     "128G",
				BleEnabled:    false,
			},
			wantErr: false,
		},
		{
			name: "With quotes",
			content: `
ARCHIVE_SYSTEM="rclone"
CIFS_USERNAME="user with space"
CIFS_PASSWORD='password with space'
`,
			want: &SystemConfig{
				ArchiveSystem: "rclone",
				CifsUsername:  "user with space",
				CifsPassword:  "password with space",
			},
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseString(tt.content)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseString() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ParseString() = %v, want %v", got, tt.want)
			}
		})
	}
}
