BINARY_NAME=audnexus-provider
BUILD_DIR=bin

.PHONY: all build build-all run test clean deps

all: build

build:
	go build -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/server

build-all:
	GOOS=linux GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 ./cmd/server
	GOOS=linux GOARCH=arm64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-linux-arm64 ./cmd/server
	GOOS=darwin GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-amd64 ./cmd/server
	GOOS=darwin GOARCH=arm64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-darwin-arm64 ./cmd/server
	GOOS=windows GOARCH=amd64 go build -o $(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe ./cmd/server

run:
	go run ./cmd/server

test:
	go test -v ./...

clean:
	rm -rf $(BUILD_DIR)/

deps:
	go mod tidy
	go mod download