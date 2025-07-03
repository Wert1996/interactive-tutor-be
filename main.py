from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.websocket_routes import router as websocket_router
from app.routes.session_routes import router as session_router

app = FastAPI(
    title="Interactive Tutor Backend",
    description="Backend API for Interactive Tutor application",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(websocket_router)
app.include_router(session_router)

@app.get("/")
async def root():
    return {"message": "Interactive Tutor Backend API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 