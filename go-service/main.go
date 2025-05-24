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

// generateHelm runs `helm template` to render a chart as Kubernetes manifests.
// Expects input["name"] (release name) and input["chart"] (chart path or name).
func generateHelm(input map[string]interface{}) map[string]interface{} {
	name, nameOk := input["name"].(string)
	chart, chartOk := input["chart"].(string)
	if !nameOk || !chartOk || name == "" || chart == "" {
		return map[string]interface{}{
			"success": false,
			"error":   "Both 'name' and 'chart' must be provided",
		}
	}

	cmd := exec.Command("helm", "template", name, chart)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   string(output) + "\n" + err.Error(),
		}
	}
	return map[string]interface{}{
		"success":  true,
		"manifest": string(output),
	}
}

// validateK8s writes a manifest to a temp file and runs `kubectl apply --dry-run=server` to validate it.
// Optionally uses input["kubeconfig"] for cluster context.
func validateK8s(input map[string]interface{}) map[string]interface{} {
	manifest, ok := input["manifest"].(string)
	if !ok || manifest == "" {
		return map[string]interface{}{
			"success": false,
			"error":   "No manifest provided",
		}
	}

	tmpfile, err := os.CreateTemp("", "k8s-validate-")
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   "Failed to create temp file: " + err.Error(),
		}
	}
	defer os.Remove(tmpfile.Name())

	if _, err := tmpfile.WriteString(manifest); err != nil {
		tmpfile.Close()
		return map[string]interface{}{
			"success": false,
			"error":   "Failed to write manifest: " + err.Error(),
		}
	}
	if err := tmpfile.Close(); err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   "Failed to close temp file: " + err.Error(),
		}
	}

	cmd := exec.Command("kubectl", "apply", "--dry-run=server", "-f", tmpfile.Name())
	if kubeconfig, ok := input["kubeconfig"].(string); ok && kubeconfig != "" {
		cmd.Env = append(os.Environ(), "KUBECONFIG="+kubeconfig)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   string(output) + "\n" + err.Error(),
		}
	}

	return map[string]interface{}{
		"success": true,
		"message": "Manifest validated successfully",
	}
}

// toJSON marshals a Go value to JSON string, returning an error JSON if marshaling fails.
func toJSON(data interface{}) string {
	bytes, err := json.Marshal(data)
	if err != nil {
		return `{"success":false,"error":"json marshal error"}`
	}
	return string(bytes)
}
