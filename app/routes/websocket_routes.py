import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.logic.websocket_manager import WebSocketManager
from app.logic.learning_interface import LearningInterface
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
manager = WebSocketManager()
learning_interface = LearningInterface()

@router.websocket("/learning-interface")
async def learning_interface_websocket(websocket: WebSocket):
    # Shared flag to signal both coroutines to stop
    should_stop = asyncio.Event()
    
    # Receive from client
    async def receive_from_client(client_buffer: asyncio.Queue):
        try:
            while not should_stop.is_set():
                try:
                    # Receive message from client
                    message = await websocket.receive_json()
                    logger.info(f"Received message: {message}")
                    
                    # Process the message based on its type
                    await learning_interface.process_message(message, client_buffer)
                    
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected in receive_from_client")
                    should_stop.set()
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    error_response = {
                        "type": "error", 
                        "message": f"Error processing message: {str(e)}"
                    }
                    try:
                        await client_buffer.put(error_response)
                    except:
                        # If we can't add to queue, connection is probably closed
                        should_stop.set()
                        break
        except Exception as e:
            logger.error(f"Unexpected error in receive_from_client: {str(e)}")
            should_stop.set()
    
    # Send to client
    async def send_to_client(client_buffer: asyncio.Queue):
        try:
            while not should_stop.is_set():
                try:
                    # Wait for message with timeout to allow checking should_stop
                    message = await asyncio.wait_for(client_buffer.get(), timeout=1.0)
                    await websocket.send_json(message)
                except asyncio.TimeoutError:
                    # Continue to check should_stop flag
                    continue
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected in send_to_client")
                    should_stop.set()
                    break
                except Exception as e:
                    logger.error(f"Error sending message: {str(e)}")
                    should_stop.set()
                    break
        except Exception as e:
            logger.error(f"Unexpected error in send_to_client: {str(e)}")
            should_stop.set()

    await manager.connect(websocket)
    logger.info("New client connected to learning interface")
    client_buffer = asyncio.Queue(maxsize=100)
    
    # Create tasks for both coroutines
    receive_task = asyncio.create_task(receive_from_client(client_buffer))
    send_task = asyncio.create_task(send_to_client(client_buffer))
    
    try:
        # Wait for either task to complete or fail
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel any remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        logger.error(f"Error in websocket connection: {str(e)}")
    finally:
        # Ensure both tasks are cancelled
        if not receive_task.done():
            receive_task.cancel()
        if not send_task.done():
            send_task.cancel()
            
        # Clean up
        manager.disconnect(websocket)
        logger.info("Client disconnected from learning interface") 
