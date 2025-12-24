"""
API Documentation Generator and Interactive Testing Interface
"""

from flask import Blueprint, render_template_string, jsonify, request
from .base_api import success_response
from .middleware import cors_headers, security_headers

docs_bp = Blueprint('api_docs', __name__, url_prefix='/api/docs')


# API Documentation Template
API_DOCS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Admin System API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #333;
        }
        .endpoint {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            margin: 20px 0;
            padding: 20px;
        }
        .method {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            margin-right: 10px;
        }
        .get { background: #28a745; color: white; }
        .post { background: #007bff; color: white; }
        .put { background: #ffc107; color: black; }
        .delete { background: #dc3545; color: white; }
        .code {
            background: #f1f3f4;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 14px;
            overflow-x: auto;
        }
        .test-form {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .test-form input, .test-form textarea, .test-form select {
            width: 100%;
            padding: 8px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .test-form button {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .test-form button:hover {
            background: #0056b3;
        }
        .response {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-top: 10px;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .nav {
            background: #343a40;
            color: white;
            padding: 15px;
            margin: -30px -30px 30px -30px;
            border-radius: 8px 8px 0 0;
        }
        .nav ul {
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-wrap: wrap;
        }
        .nav li {
            margin-right: 20px;
        }
        .nav a {
            color: #adb5bd;
            text-decoration: none;
        }
        .nav a:hover {
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <h2>Dynamic Admin System API v1.0</h2>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#authentication">Authentication</a></li>
                <li><a href="#configuration">Configuration</a></li>
                <li><a href="#content">Content</a></li>
                <li><a href="#theme">Theme</a></li>
                <li><a href="#users">Users</a></li>
                <li><a href="#products">Products</a></li>
                <li><a href="#orders">Orders</a></li>
                <li><a href="#analytics">Analytics</a></li>
                <li><a href="#system">System</a></li>
                <li><a href="#integrations">Integrations</a></li>
            </ul>
        </div>

        <section id="overview">
            <h2>Overview</h2>
            <p>The Dynamic Admin System API provides comprehensive RESTful endpoints for managing all aspects of the MarketHub Pro e-commerce platform. This API allows real-time configuration management, content editing, user management, analytics, and system monitoring without requiring server restarts.</p>
            
            <h3>Base URL</h3>
            <div class="code">{{ base_url }}/api/admin</div>
            
            <h3>Response Format</h3>
            <p>All API responses follow a consistent format:</p>
            <div class="code">{
  "success": true|false,
  "data": {...},
  "message": "Optional message",
  "error": "Error message (if success is false)",
  "code": "ERROR_CODE (if success is false)"
}</div>
        </section>

        <section id="authentication">
            <h2>Authentication</h2>
            <p>The API supports multiple authentication methods:</p>
            
            <h3>Session-based Authentication</h3>
            <p>For web interface access, use session-based authentication by logging in through the admin interface.</p>
            
            <h3>API Key Authentication</h3>
            <p>For programmatic access, include your API key in the request headers:</p>
            <div class="code">X-API-Key: your-api-key-here</div>
            
            <h3>Rate Limiting</h3>
            <p>API requests are rate limited based on the endpoint type:</p>
            <ul>
                <li>Default: 100 requests per hour</li>
                <li>Authentication: 10 requests per 5 minutes</li>
                <li>File uploads: 20 requests per hour</li>
                <li>Data exports: 5 requests per hour</li>
            </ul>
        </section>

        <!-- Configuration Endpoints -->
        <section id="configuration">
            <h2>Configuration Management</h2>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/admin/configuration/settings</h3>
                <p>Get all configuration settings with optional category filtering.</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><code>category</code> (optional): Filter by category</li>
                </ul>
                
                <div class="test-form">
                    <h4>Test this endpoint</h4>
                    <input type="text" id="config-category" placeholder="Category (optional)">
                    <button onclick="testEndpoint('/api/admin/configuration/settings', 'GET', {category: document.getElementById('config-category').value})">Test</button>
                    <div id="config-response" class="response" style="display:none;"></div>
                </div>
            </div>
            
            <div class="endpoint">
                <h3><span class="method put">PUT</span> /api/admin/configuration/settings/{key}</h3>
                <p>Update a specific configuration setting.</p>
                
                <h4>Request Body</h4>
                <div class="code">{
  "value": "new-value"
}</div>
                
                <div class="test-form">
                    <h4>Test this endpoint</h4>
                    <input type="text" id="config-key" placeholder="Setting key">
                    <textarea id="config-value" placeholder="New value (JSON)"></textarea>
                    <button onclick="testConfigUpdate()">Test</button>
                    <div id="config-update-response" class="response" style="display:none;"></div>
                </div>
            </div>
        </section>

        <!-- Content Endpoints -->
        <section id="content">
            <h2>Content Management</h2>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/admin/content/elements</h3>
                <p>List all content elements with pagination.</p>
                
                <h4>Parameters</h4>
                <ul>
                    <li><code>page</code> (optional): Page number (default: 1)</li>
                    <li><code>limit</code> (optional): Items per page (default: 20)</li>
                    <li><code>type</code> (optional): Content type filter</li>
                </ul>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/admin/content/media/upload</h3>
                <p>Upload and process media files.</p>
                
                <h4>Request</h4>
                <p>Multipart form data with file field.</p>
            </div>
        </section>

        <!-- Add more sections for other endpoints -->
        
    </div>

    <script>
        async function testEndpoint(url, method, params = {}) {
            const responseDiv = document.getElementById('config-response');
            responseDiv.style.display = 'block';
            responseDiv.textContent = 'Loading...';
            
            try {
                const queryString = Object.keys(params)
                    .filter(key => params[key])
                    .map(key => `${key}=${encodeURIComponent(params[key])}`)
                    .join('&');
                
                const fullUrl = queryString ? `${url}?${queryString}` : url;
                
                const response = await fetch(fullUrl, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                responseDiv.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                responseDiv.textContent = `Error: ${error.message}`;
            }
        }
        
        async function testConfigUpdate() {
            const key = document.getElementById('config-key').value;
            const value = document.getElementById('config-value').value;
            const responseDiv = document.getElementById('config-update-response');
            
            if (!key || !value) {
                alert('Please provide both key and value');
                return;
            }
            
            responseDiv.style.display = 'block';
            responseDiv.textContent = 'Loading...';
            
            try {
                let parsedValue;
                try {
                    parsedValue = JSON.parse(value);
                } catch {
                    parsedValue = value;
                }
                
                const response = await fetch(`/api/admin/configuration/settings/${key}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ value: parsedValue })
                });
                
                const data = await response.json();
                responseDiv.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                responseDiv.textContent = `Error: ${error.message}`;
            }
        }
    </script>
</body>
</html>
"""


@docs_bp.route('/')
@cors_headers()
@security_headers()
def api_documentation():
    """Serve interactive API documentation."""
    base_url = request.url_root.rstrip('/')
    return render_template_string(API_DOCS_TEMPLATE, base_url=base_url)


@docs_bp.route('/openapi.json')
@cors_headers()
def openapi_spec():
    """Generate OpenAPI 3.0 specification."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Dynamic Admin System API",
            "version": "1.0.0",
            "description": "Comprehensive admin API for MarketHub Pro e-commerce platform",
            "contact": {
                "name": "API Support",
                "email": "admin@markethubpro.com"
            }
        },
        "servers": [
            {
                "url": f"{request.url_root.rstrip('/')}/api/admin",
                "description": "Production server"
            }
        ],
        "security": [
            {"SessionAuth": []},
            {"ApiKeyAuth": []}
        ],
        "components": {
            "securitySchemes": {
                "SessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            },
            "schemas": {
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "data": {"type": "object"},
                        "message": {"type": "string"}
                    }
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "error": {"type": "string"},
                        "code": {"type": "string"}
                    }
                }
            }
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "API health check",
                    "responses": {
                        "200": {
                            "description": "API is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/configuration/settings": {
                "get": {
                    "summary": "Get all configuration settings",
                    "parameters": [
                        {
                            "name": "category",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Filter by category"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Configuration settings retrieved",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SuccessResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/configuration/settings/{key}": {
                "get": {
                    "summary": "Get specific configuration setting",
                    "parameters": [
                        {
                            "name": "key",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "Setting retrieved"},
                        "404": {"description": "Setting not found"}
                    }
                },
                "put": {
                    "summary": "Update configuration setting",
                    "parameters": [
                        {
                            "name": "key",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"description": "New setting value"}
                                    },
                                    "required": ["value"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Setting updated"},
                        "400": {"description": "Validation error"},
                        "404": {"description": "Setting not found"}
                    }
                }
            }
            # Add more endpoints as needed
        }
    }
    
    return jsonify(spec)


@docs_bp.route('/postman')
@cors_headers()
def postman_collection():
    """Generate Postman collection for API testing."""
    collection = {
        "info": {
            "name": "Dynamic Admin System API",
            "description": "Comprehensive admin API collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": f"{request.url_root.rstrip('/')}/api/admin",
                "type": "string"
            }
        ],
        "auth": {
            "type": "apikey",
            "apikey": [
                {
                    "key": "key",
                    "value": "X-API-Key",
                    "type": "string"
                },
                {
                    "key": "value",
                    "value": "{{apiKey}}",
                    "type": "string"
                }
            ]
        },
        "item": [
            {
                "name": "Configuration",
                "item": [
                    {
                        "name": "Get All Settings",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{baseUrl}}/configuration/settings",
                                "host": ["{{baseUrl}}"],
                                "path": ["configuration", "settings"]
                            }
                        }
                    },
                    {
                        "name": "Update Setting",
                        "request": {
                            "method": "PUT",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n  \"value\": \"new-value\"\n}"
                            },
                            "url": {
                                "raw": "{{baseUrl}}/configuration/settings/{{settingKey}}",
                                "host": ["{{baseUrl}}"],
                                "path": ["configuration", "settings", "{{settingKey}}"]
                            }
                        }
                    }
                ]
            }
            # Add more endpoint collections
        ]
    }
    
    return jsonify(collection)


def get_api_endpoints():
    """Get list of all available API endpoints."""
    endpoints = {
        "Configuration Management": {
            "base_path": "/configuration",
            "endpoints": [
                {"method": "GET", "path": "/settings", "description": "Get all settings"},
                {"method": "GET", "path": "/settings/{key}", "description": "Get specific setting"},
                {"method": "PUT", "path": "/settings/{key}", "description": "Update setting"},
                {"method": "POST", "path": "/settings", "description": "Create setting"},
                {"method": "POST", "path": "/cache/clear", "description": "Clear cache"}
            ]
        },
        "Content Management": {
            "base_path": "/content",
            "endpoints": [
                {"method": "GET", "path": "/elements", "description": "List content elements"},
                {"method": "GET", "path": "/elements/{id}", "description": "Get content element"},
                {"method": "POST", "path": "/elements", "description": "Create content element"},
                {"method": "PUT", "path": "/elements/{id}", "description": "Update content element"},
                {"method": "POST", "path": "/elements/{id}/publish", "description": "Publish content"},
                {"method": "POST", "path": "/media/upload", "description": "Upload media"}
            ]
        },
        "Theme Management": {
            "base_path": "/theme",
            "endpoints": [
                {"method": "GET", "path": "/current", "description": "Get current theme"},
                {"method": "PUT", "path": "/settings/{property}", "description": "Update theme setting"},
                {"method": "POST", "path": "/preview", "description": "Preview theme changes"},
                {"method": "POST", "path": "/backup", "description": "Backup theme"},
                {"method": "POST", "path": "/restore/{id}", "description": "Restore theme"}
            ]
        },
        "User Management": {
            "base_path": "/users",
            "endpoints": [
                {"method": "GET", "path": "/", "description": "List users"},
                {"method": "GET", "path": "/{id}", "description": "Get user"},
                {"method": "POST", "path": "/", "description": "Create user"},
                {"method": "PUT", "path": "/{id}", "description": "Update user"},
                {"method": "POST", "path": "/{id}/suspend", "description": "Suspend user"},
                {"method": "GET", "path": "/vendors/applications", "description": "List vendor applications"}
            ]
        },
        "Product Management": {
            "base_path": "/products",
            "endpoints": [
                {"method": "GET", "path": "/", "description": "List products"},
                {"method": "POST", "path": "/", "description": "Create product"},
                {"method": "PUT", "path": "/{id}", "description": "Update product"},
                {"method": "DELETE", "path": "/{id}", "description": "Delete product"},
                {"method": "POST", "path": "/bulk/update", "description": "Bulk update products"},
                {"method": "POST", "path": "/import", "description": "Import products"}
            ]
        },
        "Order Management": {
            "base_path": "/orders",
            "endpoints": [
                {"method": "GET", "path": "/", "description": "List orders"},
                {"method": "GET", "path": "/{id}", "description": "Get order"},
                {"method": "PUT", "path": "/{id}/status", "description": "Update order status"},
                {"method": "POST", "path": "/{id}/refund", "description": "Process refund"},
                {"method": "GET", "path": "/disputes", "description": "List disputes"}
            ]
        },
        "Analytics": {
            "base_path": "/analytics",
            "endpoints": [
                {"method": "GET", "path": "/dashboard", "description": "Get analytics dashboard"},
                {"method": "GET", "path": "/metrics/real-time", "description": "Get real-time metrics"},
                {"method": "POST", "path": "/reports/custom", "description": "Generate custom report"},
                {"method": "GET", "path": "/predictive", "description": "Get predictive analytics"}
            ]
        },
        "System Management": {
            "base_path": "/system",
            "endpoints": [
                {"method": "GET", "path": "/health", "description": "Get system health"},
                {"method": "GET", "path": "/performance", "description": "Get performance metrics"},
                {"method": "POST", "path": "/backups", "description": "Create backup"},
                {"method": "POST", "path": "/cache/clear", "description": "Clear cache"}
            ]
        },
        "Integration Management": {
            "base_path": "/integrations",
            "endpoints": [
                {"method": "GET", "path": "/", "description": "List integrations"},
                {"method": "POST", "path": "/payment-gateways", "description": "Configure payment gateway"},
                {"method": "POST", "path": "/shipping", "description": "Configure shipping integration"},
                {"method": "POST", "path": "/email", "description": "Configure email service"}
            ]
        }
    }
    
    return endpoints


@docs_bp.route('/endpoints')
@cors_headers()
def list_endpoints():
    """Get structured list of all API endpoints."""
    return jsonify(success_response(get_api_endpoints()))