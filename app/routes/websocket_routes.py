import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.logic.websocket_manager import WebSocketManager
from app.logic.learning_interface import LearningInterface
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
manager = WebSocketManager()

@router.websocket("/learning-interface")
async def learning_interface_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("New client connected to learning interface")
    
    # Create a new LearningInterface instance for this connection
    learning_interface = LearningInterface(websocket)
    
    try:
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_json()
                logger.info(f"Received message: {message}")
                
                # Process the message directly
                await learning_interface.process_message(message)
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "type": "error", 
                    "message": f"Error processing message: {str(e)}"
                })
                
    except Exception as e:
        logger.error(f"Error in websocket connection: {str(e)}")
    finally:
        # Clean up
        manager.disconnect(websocket)
        logger.info("Client disconnected from learning interface") 
