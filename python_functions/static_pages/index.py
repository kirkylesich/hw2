"""
Cloud Function: Static Pages
Handles GET / and GET /tasks (HTML) requests
"""
import json
import os


# HTML templates embedded at compile time
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lecture Notes Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        form {
            background: #f4f4f4;
            padding: 20px;
            border-radius: 8px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
        .link {
            margin-top: 20px;
        }
        .link a {
            color: #007bff;
            text-decoration: none;
        }
        .link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>Lecture Notes Generator</h1>
    <p>Generate PDF lecture notes from Yandex Disk video links</p>
    
    <form action="/tasks" method="POST">
        <label for="title">Lecture Title:</label>
        <input type="text" id="title" name="title" required>
        
        <label for="video_link">Yandex Disk Public Link:</label>
        <input type="text" id="video_link" name="video_link" required placeholder="https://disk.yandex.ru/...">
        
        <button type="submit">Generate Notes</button>
    </form>
    
    <div class="link">
        <a href="/tasks">View All Tasks</a>
    </div>
</body>
</html>
"""

TASKS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tasks - Lecture Notes Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 50px auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #007bff;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status {
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        .status-queued {
            background-color: #ffc107;
            color: #000;
        }
        .status-processing {
            background-color: #17a2b8;
            color: #fff;
        }
        .status-completed {
            background-color: #28a745;
            color: #fff;
        }
        .status-error {
            background-color: #dc3545;
            color: #fff;
        }
        .link {
            margin-top: 20px;
        }
        .link a {
            color: #007bff;
            text-decoration: none;
        }
        .link a:hover {
            text-decoration: underline;
        }
        .download-link {
            color: #28a745;
            text-decoration: none;
            font-weight: bold;
        }
        .download-link:hover {
            text-decoration: underline;
        }
        .error-message {
            color: #dc3545;
            font-size: 0.9em;
        }
    </style>
    <script>
        // Auto-refresh every 10 seconds
        setTimeout(function() {
            location.reload();
        }, 10000);
    </script>
</head>
<body>
    <h1>Lecture Notes Tasks</h1>
    <p>Tasks are automatically refreshed every 10 seconds</p>
    
    <div id="tasks-container">
        <p>Loading tasks...</p>
    </div>
    
    <div class="link">
        <a href="/">Create New Task</a>
    </div>
    
    <script>
        // Fetch tasks from API
        fetch('/api/tasks')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('tasks-container');
                
                if (data.tasks && data.tasks.length > 0) {
                    let html = '<table><thead><tr>';
                    html += '<th>Created</th>';
                    html += '<th>Title</th>';
                    html += '<th>Status</th>';
                    html += '<th>Action</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.tasks.forEach(task => {
                        html += '<tr>';
                        html += `<td>${new Date(task.created_at).toLocaleString()}</td>`;
                        html += `<td>${task.title}</td>`;
                        html += `<td><span class="status status-${task.status}">${task.status}</span></td>`;
                        html += '<td>';
                        
                        if (task.status === 'completed' && task.pdf_url) {
                            html += `<a href="${task.pdf_url}" class="download-link">Download PDF</a>`;
                        } else if (task.status === 'error' && task.error_message) {
                            html += `<span class="error-message">${task.error_message}</span>`;
                        } else {
                            html += '-';
                        }
                        
                        html += '</td>';
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table>';
                    container.innerHTML = html;
                } else {
                    container.innerHTML = '<p>No tasks found. <a href="/">Create your first task</a></p>';
                }
            })
            .catch(error => {
                console.error('Error fetching tasks:', error);
                document.getElementById('tasks-container').innerHTML = '<p>Error loading tasks. Please refresh the page.</p>';
            });
    </script>
</body>
</html>
"""


def handler(event, context):
    """
    Main handler for Cloud Function
    
    Args:
        event: Request event from API Gateway
        context: Function execution context
        
    Returns:
        dict: HTTP response with status code, headers, and body
    """
    try:
        # Extract path from request - API Gateway format
        # Try multiple possible locations for the path
        path = None
        
        # Try requestContext.requestPath (API Gateway format)
        if 'requestContext' in event and 'requestPath' in event['requestContext']:
            path = event['requestContext']['requestPath']
        # Try url field
        elif 'url' in event:
            path = event['url']
        # Try path field
        elif 'path' in event:
            path = event['path']
        # Try httpMethod and resource
        elif 'resource' in event:
            path = event['resource']
        else:
            path = '/'
        
        # Normalize path
        if not path or path == '':
            path = '/'
        
        # Remove query string if present
        if '?' in path:
            path = path.split('?')[0]
            
        # Route based on path
        if path == '/':
            # Serve index page (create task form)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html; charset=utf-8',
                },
                'body': INDEX_HTML,
            }
        elif path == '/tasks' or path.startswith('/tasks'):
            # Serve tasks list page
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html; charset=utf-8',
                },
                'body': TASKS_HTML,
            }
        else:
            # 404 Not Found - include debug info
            debug_info = f"Path: {path}, Event keys: {list(event.keys())}"
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'text/html; charset=utf-8',
                },
                'body': f'<h1>404 - Page Not Found</h1><p>{debug_info}</p>',
            }
            
    except Exception as e:
        # Infrastructure error
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'}),
        }
