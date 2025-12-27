import os
import sys
import json
import logging
from flask import Flask, request, jsonify
from processor import process_task

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/", methods=["POST"])
def handle_trigger():
    try:
        data = request.get_json()
        logger.info(f"Received trigger request: {json.dumps(data)}")
        
        if not data or "messages" not in data:
            logger.error("Invalid request format: missing 'messages' field")
            return jsonify({"status": "error", "message": "Invalid request format"}), 200
        
        messages = data["messages"]
        
        for message in messages:
            try:
                message_body = message.get("details", {}).get("message", {}).get("body", "{}")
                logger.info(f"Processing message body: {message_body}")
                
                message_data = json.loads(message_body)
                task_id = message_data.get("task_id")
                
                if not task_id:
                    logger.error("Missing task_id in message")
                    continue
                
                logger.info(f"Processing task: {task_id}")
                
                process_task(task_id)
                
                logger.info(f"Task {task_id} processed successfully")
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                continue
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error handling trigger request: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Waitress server on 0.0.0.0:{port}")
    
    from waitress import serve
    serve(app, host="0.0.0.0", port=port, threads=4)
