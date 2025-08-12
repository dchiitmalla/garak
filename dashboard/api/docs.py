"""
OpenAPI specification and Swagger documentation for Garak Dashboard API.

This module generates OpenAPI/Swagger documentation for the public API
and serves interactive documentation via Swagger UI.
"""

from flask import Blueprint, jsonify, render_template_string
from flask_swagger_ui import get_swaggerui_blueprint
import json

# Blueprint for API documentation
api_docs = Blueprint('api_docs', __name__)

# OpenAPI specification
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Garak LLM Security Scanner API",
        "description": """
Public API for the Garak AI red-teaming framework. Garak is a comprehensive LLM vulnerability scanner 
that probes for hallucination, data leakage, prompt injection, misinformation, toxicity generation, 
jailbreaks, and other security weaknesses in language models.

## Authentication

All API endpoints require authentication using API keys. Include your API key in one of these ways:

- **Authorization header**: `Authorization: Bearer your_api_key_here`
- **X-API-Key header**: `X-API-Key: your_api_key_here`
- **Query parameter**: `?api_key=your_api_key_here` (less secure)

## Rate Limiting

API requests are rate limited based on your API key permissions:
- **Read operations**: 100 requests per minute
- **Write operations**: 50 requests per minute  
- **Scan creation**: 10 requests per minute
- **Admin operations**: Varies by operation

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Scan Workflow

1. **Discover capabilities**: Use `/api/v1/generators` and `/api/v1/probes` to see available options
2. **Create scan**: POST to `/api/v1/scans` with your configuration
3. **Monitor progress**: GET `/api/v1/scans/{scan_id}/progress` for real-time updates
4. **Get results**: GET `/api/v1/scans/{scan_id}` when completed
5. **Download reports**: GET `/api/v1/scans/{scan_id}/reports/{type}` for detailed reports
        """,
        "version": "1.0.0",
        "contact": {
            "name": "Garak Support",
            "url": "https://github.com/NVIDIA/garak",
            "email": "support@garak.ai"
        },
        "license": {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
        }
    },
    "servers": [
        {
            "url": "/api/v1",
            "description": "Production API"
        }
    ],
    "security": [
        {
            "ApiKeyAuth": []
        }
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authentication. Can also be provided as 'Authorization: Bearer {api_key}'"
            }
        },
        "schemas": {
            "ScanStatus": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed", "cancelled"],
                "description": "Current status of a security scan"
            },
            "ReportType": {
                "type": "string", 
                "enum": ["json", "jsonl", "html", "hits"],
                "description": "Type of report file available for download"
            },
            "PermissionType": {
                "type": "string",
                "enum": ["read", "write", "admin"],
                "description": "API key permission level"
            },
            "CreateScanRequest": {
                "type": "object",
                "required": ["generator", "model_name"],
                "properties": {
                    "generator": {
                        "type": "string",
                        "description": "Model generator type",
                        "enum": ["openai", "huggingface", "cohere", "anthropic", "ollama", "replicate", "vertexai", "llamacpp", "mistral", "litellm"]
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Specific model name to test",
                        "example": "gpt-3.5-turbo"
                    },
                    "probe_categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of probe categories to run",
                        "example": ["dan", "security", "toxicity"]
                    },
                    "probes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific probes to run (overrides categories)",
                        "example": ["dan.Dan_11_0", "promptinject.HijackKillHumans"]
                    },
                    "api_keys": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "API keys for model access",
                        "example": {"openai_api_key": "sk-..."}
                    },
                    "parallel_attempts": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                        "description": "Number of parallel attempts per probe"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable name for the scan",
                        "example": "GPT-3.5 Security Assessment"
                    },
                    "description": {
                        "type": "string", 
                        "description": "Description of the scan purpose",
                        "example": "Testing GPT-3.5-turbo for DAN attacks and prompt injection vulnerabilities"
                    }
                }
            },
            "ScanProgressInfo": {
                "type": "object",
                "properties": {
                    "completed_items": {"type": "integer", "description": "Number of completed test items"},
                    "total_items": {"type": "integer", "description": "Total number of test items"},
                    "progress_percent": {"type": "number", "minimum": 0, "maximum": 100, "description": "Progress percentage"},
                    "elapsed_time": {"type": "string", "description": "Time elapsed since scan start"},
                    "estimated_remaining": {"type": "string", "description": "Estimated time remaining"},
                    "estimated_completion": {"type": "string", "description": "Estimated completion time"}
                }
            },
            "ScanMetadata": {
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string", "description": "Unique scan identifier"},
                    "name": {"type": "string", "description": "Human-readable scan name"},
                    "description": {"type": "string", "description": "Scan description"},
                    "generator": {"type": "string", "description": "Model generator used"},
                    "model_name": {"type": "string", "description": "Model name tested"},
                    "probe_categories": {"type": "array", "items": {"type": "string"}, "description": "Probe categories run"},
                    "probes": {"type": "array", "items": {"type": "string"}, "description": "Specific probes executed"},
                    "status": {"$ref": "#/components/schemas/ScanStatus"},
                    "created_at": {"type": "string", "format": "date-time", "description": "Scan creation timestamp"},
                    "started_at": {"type": "string", "format": "date-time", "description": "Scan start timestamp"},
                    "completed_at": {"type": "string", "format": "date-time", "description": "Scan completion timestamp"},
                    "duration_seconds": {"type": "number", "description": "Total scan duration"},
                    "parallel_attempts": {"type": "integer", "description": "Number of parallel attempts"},
                    "progress": {"$ref": "#/components/schemas/ScanProgressInfo"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "required": ["error", "message"],
                "properties": {
                    "error": {"type": "string", "description": "Error type or code"},
                    "message": {"type": "string", "description": "Human-readable error message"},
                    "details": {"type": "object", "description": "Additional error details"},
                    "timestamp": {"type": "string", "format": "date-time", "description": "Error timestamp"}
                }
            }
        },
        "responses": {
            "UnauthorizedError": {
                "description": "Authentication required",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "ForbiddenError": {
                "description": "Insufficient permissions",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "NotFoundError": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "RateLimitError": {
                "description": "Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                },
                "headers": {
                    "X-RateLimit-Limit": {"schema": {"type": "integer"}},
                    "X-RateLimit-Remaining": {"schema": {"type": "integer"}},
                    "X-RateLimit-Reset": {"schema": {"type": "integer"}}
                }
            },
            "ValidationError": {
                "description": "Request validation failed",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            }
        }
    },
    "paths": {
        "/scans": {
            "post": {
                "summary": "Create a new security scan",
                "description": "Start a new garak security scan with specified model and probes",
                "tags": ["Scan Management"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateScanRequest"},
                            "examples": {
                                "openai_dan_scan": {
                                    "summary": "OpenAI GPT-3.5 DAN Attack Test",
                                    "value": {
                                        "generator": "openai",
                                        "model_name": "gpt-3.5-turbo",
                                        "probe_categories": ["dan", "security"],
                                        "api_keys": {"openai_api_key": "sk-your-key-here"},
                                        "name": "GPT-3.5 DAN Test",
                                        "description": "Testing GPT-3.5-turbo for DAN attacks"
                                    }
                                },
                                "huggingface_scan": {
                                    "summary": "Hugging Face Model Test",
                                    "value": {
                                        "generator": "huggingface", 
                                        "model_name": "gpt2",
                                        "probe_categories": ["toxicity", "hallucination"],
                                        "parallel_attempts": 2,
                                        "name": "GPT-2 Safety Test"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Scan created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "scan_id": {"type": "string"},
                                        "message": {"type": "string"},
                                        "metadata": {"$ref": "#/components/schemas/ScanMetadata"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "403": {"$ref": "#/components/responses/ForbiddenError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            },
            "get": {
                "summary": "List all scans",
                "description": "Get a paginated list of all security scans",
                "tags": ["Scan Management"],
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 1, "default": 1},
                        "description": "Page number for pagination"
                    },
                    {
                        "name": "per_page", 
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                        "description": "Number of scans per page"
                    },
                    {
                        "name": "status",
                        "in": "query", 
                        "schema": {"$ref": "#/components/schemas/ScanStatus"},
                        "description": "Filter by scan status"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "List of scans",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "scans": {"type": "array", "items": {"$ref": "#/components/schemas/ScanMetadata"}},
                                        "total": {"type": "integer"},
                                        "page": {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "has_next": {"type": "boolean"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            }
        },
        "/scans/{scan_id}": {
            "get": {
                "summary": "Get scan details",
                "description": "Get detailed information about a specific scan including results and reports",
                "tags": ["Scan Management"],
                "parameters": [
                    {
                        "name": "scan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Unique scan identifier"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Detailed scan information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "metadata": {"$ref": "#/components/schemas/ScanMetadata"},
                                        "results": {"type": "object", "description": "Scan results (if completed)"},
                                        "reports": {"type": "array", "items": {"type": "object"}},
                                        "output_log": {"type": "string", "description": "Scan output log"}
                                    }
                                }
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFoundError"},
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            },
            "delete": {
                "summary": "Cancel a scan",
                "description": "Cancel a running or pending scan",
                "tags": ["Scan Management"],
                "parameters": [
                    {
                        "name": "scan_id", 
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Unique scan identifier"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Scan cancelled successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"},
                                        "status": {"$ref": "#/components/schemas/ScanStatus"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {"description": "Scan cannot be cancelled"},
                    "404": {"$ref": "#/components/responses/NotFoundError"},
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            }
        },
        "/generators": {
            "get": {
                "summary": "List available generators",
                "description": "Get a list of all available model generators and their capabilities",
                "tags": ["Discovery"],
                "responses": {
                    "200": {
                        "description": "List of available generators",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "generators": {"type": "array", "items": {"type": "object"}},
                                        "total": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            }
        },
        "/probes": {
            "get": {
                "summary": "List available probe categories",
                "description": "Get a list of all available probe categories and their individual probes",
                "tags": ["Discovery"],
                "responses": {
                    "200": {
                        "description": "List of probe categories and probes",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "categories": {"type": "array", "items": {"type": "object"}},
                                        "total_categories": {"type": "integer"},
                                        "total_probes": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/UnauthorizedError"},
                    "429": {"$ref": "#/components/responses/RateLimitError"}
                }
            }
        }
    },
    "tags": [
        {
            "name": "Scan Management",
            "description": "Create, monitor, and manage security scans"
        },
        {
            "name": "Discovery", 
            "description": "Discover available generators, models, and probes"
        },
        {
            "name": "Admin",
            "description": "Administrative operations for API key management"
        }
    ]
}


@api_docs.route('/openapi.json')
def openapi_spec():
    """Serve the OpenAPI specification as JSON."""
    return jsonify(OPENAPI_SPEC)


def create_swagger_blueprint():
    """Create Swagger UI blueprint."""
    # Swagger UI configuration
    swagger_url = '/api/docs'
    api_url = '/openapi.json'
    
    swaggerui_blueprint = get_swaggerui_blueprint(
        swagger_url,
        api_url,
        config={
            'app_name': "Garak LLM Security Scanner API",
            'supportedSubmitMethods': ['get', 'post', 'put', 'delete', 'patch'],
            'validatorUrl': None,  # Disable validator
            'displayRequestDuration': True,
            'docExpansion': 'list',
            'defaultModelsExpandDepth': 2,
            'deepLinking': True,
            'showExtensions': True,
            'showCommonExtensions': True,
            'tryItOutEnabled': True
        }
    )
    
    return swaggerui_blueprint


# Custom documentation pages

@api_docs.route('/api/docs/examples')
def api_examples():
    """Serve API usage examples."""
    examples_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Garak API Examples</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .example { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .example h3 { color: #2c5aa0; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Garak API Usage Examples</h1>
    
    <div class="example">
        <h3>1. Create an Admin API Key (Bootstrap)</h3>
        <p>First, create the initial admin API key for system setup:</p>
        <pre><code>curl -X POST http://localhost:8000/api/v1/admin/bootstrap \\
  -H "Content-Type: application/json"</code></pre>
        <p>Save the returned API key securely - it won't be shown again!</p>
    </div>
    
    <div class="example">
        <h3>2. Create a Regular API Key</h3>
        <p>Use your admin key to create regular API keys:</p>
        <pre><code>curl -X POST http://localhost:8000/api/v1/admin/api-keys \\
  -H "X-API-Key: your_admin_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Scan Key",
    "description": "For running security scans",
    "permissions": ["read", "write"],
    "rate_limit": 100
  }'</code></pre>
    </div>
    
    <div class="example">
        <h3>3. List Available Generators and Probes</h3>
        <p>Discover what's available before creating scans:</p>
        <pre><code># List generators
curl -X GET http://localhost:8000/api/v1/generators \\
  -H "X-API-Key: your_api_key_here"

# List probe categories  
curl -X GET http://localhost:8000/api/v1/probes \\
  -H "X-API-Key: your_api_key_here"</code></pre>
    </div>
    
    <div class="example">
        <h3>4. Create a Security Scan</h3>
        <p>Start a scan with OpenAI GPT-3.5:</p>
        <pre><code>curl -X POST http://localhost:8000/api/v1/scans \\
  -H "X-API-Key: your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "generator": "openai",
    "model_name": "gpt-3.5-turbo", 
    "probe_categories": ["dan", "security"],
    "api_keys": {
      "openai_api_key": "sk-your-openai-key"
    },
    "name": "GPT-3.5 Security Test",
    "description": "Testing for DAN attacks and security vulnerabilities"
  }'</code></pre>
    </div>
    
    <div class="example">
        <h3>5. Monitor Scan Progress</h3>
        <p>Check scan status and progress:</p>
        <pre><code># Get scan status
curl -X GET http://localhost:8000/api/v1/scans/{scan_id}/status \\
  -H "X-API-Key: your_api_key_here"

# Get detailed progress  
curl -X GET http://localhost:8000/api/v1/scans/{scan_id}/progress \\
  -H "X-API-Key: your_api_key_here"</code></pre>
    </div>
    
    <div class="example">
        <h3>6. Download Results</h3>
        <p>Get results and download reports when scan completes:</p>
        <pre><code># Get scan details and results
curl -X GET http://localhost:8000/api/v1/scans/{scan_id} \\
  -H "X-API-Key: your_api_key_here"

# Download JSON report
curl -X GET http://localhost:8000/api/v1/scans/{scan_id}/reports/json \\
  -H "X-API-Key: your_api_key_here" \\
  -o scan_report.json

# Download HTML report
curl -X GET http://localhost:8000/api/v1/scans/{scan_id}/reports/html \\
  -H "X-API-Key: your_api_key_here" \\
  -o scan_report.html</code></pre>
    </div>
    
    <div class="example">
        <h3>7. Python SDK Example</h3>
        <p>Using the API with Python requests:</p>
        <pre><code>import requests
import time

# Configuration
API_BASE = "http://localhost:8000/api/v1"
API_KEY = "your_api_key_here"
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Create a scan
scan_data = {
    "generator": "huggingface",
    "model_name": "gpt2", 
    "probe_categories": ["toxicity", "hallucination"],
    "name": "GPT-2 Safety Test"
}

response = requests.post(f"{API_BASE}/scans", json=scan_data, headers=headers)
scan_id = response.json()["scan_id"]
print(f"Created scan: {scan_id}")

# Monitor progress
while True:
    response = requests.get(f"{API_BASE}/scans/{scan_id}/status", headers=headers)
    status = response.json()["status"]
    print(f"Status: {status}")
    
    if status in ["completed", "failed", "cancelled"]:
        break
        
    time.sleep(30)  # Check every 30 seconds

# Get results
response = requests.get(f"{API_BASE}/scans/{scan_id}", headers=headers)
results = response.json()
print("Scan completed:", results["metadata"]["status"])</code></pre>
    </div>
    
    <div class="example">
        <h3>8. Error Handling</h3>
        <p>API responses include detailed error information:</p>
        <pre><code># Example error response
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [
    {
      "loc": ["generator"],
      "msg": "Invalid generator: invalid_gen. Valid options: [...]",
      "type": "value_error"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}</code></pre>
    </div>
    
    <p><a href="/api/docs">← Back to API Documentation</a></p>
</body>
</html>
    """
    return examples_html