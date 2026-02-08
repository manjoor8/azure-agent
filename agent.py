import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from config import logger, validate_config, PORT
from models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, Message, ChatCompletionUsage
from intent_handler import IntentHandler

app = FastAPI(title="Azure-Agent API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

intent_handler = IntentHandler()

@app.middleware("http")
async def log_requests(request, call_next):
    # Skip logging for OPTIONS/Preflight requests to keep logs clean
    if request.method == "OPTIONS":
        return await call_next(request)
        
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Azure-Agent...")
    if not validate_config():
        logger.warning("Configuration is incomplete. Azure SDK calls will likely fail until .env is properly configured.")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "Azure-Agent"}

@app.get("/")
@app.get("/v1")
@app.get("/v1/")
async def v1_root():
    """Satisfy root-level connection pings from various versions of WebUI."""
    return {"status": "online", "message": "Azure-Agent API is active"}

@app.get("/models")
@app.get("/v1/models")
@app.get("/v1/models/")
async def list_models():
    """Detailed dummy endpoint to satisfy OpenAI API connection checks."""
    return {
        "object": "list",
        "data": [
            {
                "id": "azure-agent",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "azure-agent",
                "permission": [],
                "root": "azure-agent",
                "parent": None
            }
        ]
    }

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    try:
        # Extract the last user message
        user_message = next((m.content for m in reversed(request.messages) if m.role == "user"), None)
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found in request")

        # Process the query through the intent handler in a background thread
        response_text = await run_in_threadpool(intent_handler.process_query, user_message)

        # Build response
        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4()}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=response_text),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=len(user_message.split()),
                completion_tokens=len(response_text.split()),
                total_tokens=len(user_message.split()) + len(response_text.split())
            )
        )
        return response

    except Exception as e:
        logger.error(f"Error processing chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
