import time
import uuid
from fastapi import FastAPI, HTTPException
from config import logger, validate_config, PORT
from models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice, Message, ChatCompletionUsage
from intent_handler import IntentHandler

app = FastAPI(title="Azure-Agent API", version="1.0.0")
intent_handler = IntentHandler()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Azure-Agent...")
    if not validate_config():
        logger.warning("Configuration is incomplete. Azure SDK calls will likely fail until .env is properly configured.")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "Azure-Agent"}

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    try:
        # Extract the last user message
        user_message = next((m.content for m in reversed(request.messages) if m.role == "user"), None)
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found in request")

        # Process the query through the intent handler
        response_text = intent_handler.process_query(user_message)

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
