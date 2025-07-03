from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.logic.websocket_manager import WebSocketManager
from app.logic.learning_interface import LearningInterface
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
manager = WebSocketManager()
learning_interface = LearningInterface()

@router.websocket("/learning-interface")
async def learning_interface_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("New client connected to learning interface")
    
    try:
        while True:
            # Receive message from client
            try:
                message = await websocket.receive_json()
                logger.info(f"Received message: {message}")
                
                # Process the message based on its type
                response = await learning_interface.process_message(message)
                
                # Send response back to client
                await websocket.send_text(json.dumps(response))
                
            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format"
                }
                await websocket.send_text(json.dumps(error_response))
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                error_response = {
                    "type": "error", 
                    "message": f"Error processing message: {str(e)}"
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from learning interface") 