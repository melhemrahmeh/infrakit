package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
)

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Command required: generate-helm or validate-k8s")
	}

	cmd := os.Args[1]
	var input map[string]interface{}

	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		log.Fatal(err)
	}

	switch cmd {
	case "generate-helm":
		result := generateHelm(input)
		fmt.Println(toJSON(result))
	case "validate-k8s":
		result := validateK8s(input)
		fmt.Println(toJSON(result))
	default:
		log.Fatal("Unknown command")
	}
}

func generateHelm(input map[string]interface{}) map[string]interface{} {
	cmd := exec.Command("helm", "template", 
		input["name"].(string),
		input["chart"].(string))
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": string(output),
		}
	}
	return map[string]interface{}{
		"success": true,
		"manifest": string(output),
	}
}

func validateK8s(input map[string]interface{}) map[string]interface{} {
	manifest, ok := input["manifest"].(string)
	if !ok {
		return map[string]interface{}{
			"success": false,
			"error": "No manifest provided",
		}
	}

	// Write manifest to temp file
	tmpfile, err := os.CreateTemp("", "k8s-validate-")
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": err.Error(),
		}
	}
	defer os.Remove(tmpfile.Name())

	if _, err := tmpfile.WriteString(manifest); err != nil {
		return map[string]interface{}{
			"success": false,
			"error": err.Error(),
		}
	}
	tmpfile.Close()

	// Run kubectl validate
	cmd := exec.Command("kubectl", "apply", "--dry-run=server", "-f", tmpfile.Name())
	if kubeconfig, ok := input["kubeconfig"].(string); ok {
		cmd.Env = append(os.Environ(), "KUBECONFIG="+kubeconfig)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": string(output),
		}
	}

	return map[string]interface{}{
		"success": true,
		"message": "Manifest validated successfully",
	}
}

func toJSON(data interface{}) string {
	bytes, err := json.Marshal(data)
	if err != nil {
		return `{"success":false,"error":"json marshal error"}`
	}
	return string(bytes)
}