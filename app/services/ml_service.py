import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from app.core.config import settings
import asyncio
from typing import Optional, List, Dict, Any
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class MLService:
    def __init__(self):
        self.chat_model = None
        self.chat_tokenizer = None
        self.sentiment_pipeline = None
        self.device = "cpu"
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize ML models from local files"""
        if self.is_initialized:
            logger.info("ML Service already initialized")
            return
        
        logger.info("="*60)
        logger.info("Starting ML Service initialization...")
        logger.info("="*60)
        await asyncio.to_thread(self._load_models)
        self.is_initialized = True
        logger.info("="*60)
        logger.info("ML Service initialization complete")
        logger.info("="*60)
    
    def _load_models(self):
        try:
            # Get model paths from settings
            model_path = getattr(settings, 'MODEL_PATH', '/models/healhub-tinyllama-1.1B-Chat')
            sentiment_path = getattr(settings, 'SENTIMENT_MODEL_PATH', '/models/sentiment_model')
            
            # Validate chat model path
            logger.info(f"Loading chat model from: {model_path}")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model directory not found: {model_path}")
            
            # Check for required files
            required_files = {
                'config.json': 'Model configuration',
                'tokenizer_config.json': 'Tokenizer configuration',
            }
            
            # Check for model weights
            model_file = None
            if os.path.exists(os.path.join(model_path, 'model.safetensors')):
                model_file = 'model.safetensors'
            elif os.path.exists(os.path.join(model_path, 'pytorch_model.bin')):
                model_file = 'pytorch_model.bin'
            
            if not model_file:
                raise FileNotFoundError(
                    f"No model weights found in {model_path}. "
                    f"Expected 'model.safetensors' or 'pytorch_model.bin'"
                )
            
            logger.info(f"Found model weights: {model_file}")
            
            # Verify required files
            for filename, description in required_files.items():
                file_path = os.path.join(model_path, filename)
                if os.path.exists(file_path):
                    logger.info(f"Found {description}: {filename}")
                else:
                    logger.warning(f"Missing {description}: {filename}")
            
            # Load chat model
            logger.info("Loading chat model into memory...")
            self.chat_model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                local_files_only=True,
            )
            self.chat_model.eval()
            logger.info("Chat model loaded successfully")
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.chat_tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                local_files_only=True,
            )
            
            if self.chat_tokenizer.pad_token is None:
                self.chat_tokenizer.pad_token = self.chat_tokenizer.eos_token
            logger.info("Tokenizer loaded successfully")
            
            # Load sentiment model
            logger.info(f"Loading sentiment model from: {sentiment_path}")
            if not os.path.exists(sentiment_path):
                raise FileNotFoundError(f"Sentiment model directory not found: {sentiment_path}")
            
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=sentiment_path,
                tokenizer=sentiment_path,
                device=-1,
                local_files_only=True,
            )
            logger.info("Sentiment model loaded successfully")
            
            # Summary
            logger.info("")
            logger.info("Model Loading Summary:")
            logger.info(f"  Chat Model: {model_path}")
            logger.info(f"  Sentiment Model: {sentiment_path}")
            logger.info(f"  Device: {self.device}")
            logger.info(f"  Status: Ready")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}", exc_info=True)
            raise
    
    async def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        """Generate chat response"""
        if not self.is_initialized:
            logger.error("ML Service not initialized")
            raise RuntimeError("ML Service not initialized. Please wait for startup to complete.")
        
        try:
            # Build prompt in ChatML format
            prompt = "<|system|>\nYou are a compassionate mental health support assistant. You provide empathetic, non-judgmental support and encouragement. You listen actively and help users explore their feelings.</s>\n"
            
            # Add conversation history (last 10 messages for context)
            for msg in conversation_history[-10:]:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    prompt += f"<|user|>\n{content}</s>\n"
                else:
                    prompt += f"<|assistant|>\n{content}</s>\n"
            
            prompt += "<|assistant|>\n"
            
            logger.info(f"Generating response for prompt of length {len(prompt)}")
            
            # Generate response
            response = await asyncio.to_thread(self._generate, prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise
    
    def _generate(self, prompt: str) -> str:
        try:
            inputs = self.chat_tokenizer(
                prompt, 
                return_tensors="pt",
                truncation=True,
                max_length=1024
            )
            
            with torch.no_grad():
                outputs = self.chat_model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.chat_tokenizer.eos_token_id,
                    eos_token_id=self.chat_tokenizer.eos_token_id
                )
            
            # Decode the full output
            full_response = self.chat_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the assistant's response (after the last <|assistant|> tag)
            if "<|assistant|>" in full_response:
                response = full_response.split("<|assistant|>")[-1].strip()
            else:
                # Fallback: remove the input prompt
                response = full_response[len(prompt):].strip()
            
            # If response is empty or too short, provide a default
            if not response or len(response) < 10:
                response = "I hear you. Can you tell me more about what you're experiencing?"
            
            logger.info(f"Generated response: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error in _generate: {str(e)}", exc_info=True)
            raise
    
    async def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        if not self.is_initialized:
            logger.warning("ML Service not initialized for sentiment analysis")
            return {"label": "NEUTRAL", "score": 0.0}
        
        try:
            result = await asyncio.to_thread(self.sentiment_pipeline, text[:512])
            sentiment = result[0]
            score = sentiment['score'] if sentiment['label'] == 'POSITIVE' else -sentiment['score']
            return {
                "label": sentiment['label'],
                "score": score
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}", exc_info=True)
            return {"label": "NEUTRAL", "score": 0.0}
    
    async def calculate_risk_score(self, text: str, sentiment_score: float) -> float:
        """Calculate mental health risk score"""
        try:
            high_risk_keywords = [
                'suicide', 'kill myself', 'end it all', 'no point', 'hopeless',
                'want to die', 'better off dead', 'cant go on', "can't go on"
            ]
            medium_risk_keywords = [
                'depressed', 'anxious', 'panic', 'scared', 'alone', 'worthless',
                'helpless', 'empty', 'numb', 'desperate', 'overwhelmed'
            ]
            
            text_lower = text.lower()
            risk_score = 0.0
            
            for keyword in high_risk_keywords:
                if keyword in text_lower:
                    risk_score += 0.3
            
            for keyword in medium_risk_keywords:
                if keyword in text_lower:
                    risk_score += 0.1
            
            if sentiment_score < -0.5:
                risk_score += 0.2
            elif sentiment_score < -0.3:
                risk_score += 0.1
            
            return min(risk_score, 1.0)
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}", exc_info=True)
            return 0.0

# Global ML service instance
ml_service = MLService()