import uvicorn
from app.config import settings

if __name__ == "__main__":
    # Start the FastAPI application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENV == "development"
    ) 