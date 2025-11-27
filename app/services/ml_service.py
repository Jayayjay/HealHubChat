import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel, PeftConfig  # Add this import
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
            model_path = getattr(settings, 'MODEL_PATH', '/models/Finetuned-Llama-3B-HealHub')
            base_model_path = getattr(settings, 'BASE_MODEL_PATH', 'meta-llama/Llama-3.2-3B-Instruct')  # Add base model path
            sentiment_path = getattr(settings, 'SENTIMENT_MODEL_PATH', '/models/sentiment_model')
            
            # Validate chat model path
            logger.info(f"Loading chat model from: {model_path}")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model directory not found: {model_path}")
            
            # Check for adapter files (LoRA fine-tuning)
            adapter_files = {
                'adapter_config.json': 'Adapter configuration',
                'adapter_model.safetensors': 'Adapter weights',
            }
            
            # Check if this is a LoRA adapter or full model
            is_adapter = all(os.path.exists(os.path.join(model_path, filename)) 
                           for filename in ['adapter_config.json', 'adapter_model.safetensors'])
            
            if is_adapter:
                logger.info("Detected LoRA adapter files - loading with base model")
                logger.info(f"Base model: {base_model_path}")
                
                # Verify adapter files
                for filename, description in adapter_files.items():
                    file_path = os.path.join(model_path, filename)
                    if os.path.exists(file_path):
                        logger.info(f"Found {description}: {filename}")
                    else:
                        raise FileNotFoundError(f"Missing adapter file: {filename}")
                
                # Load base model first
                logger.info("Loading base model...")
                base_model = AutoModelForCausalLM.from_pretrained(
                    base_model_path,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                    local_files_only=False,  # Need to download base model if not cached
                )
                
                # Load adapter
                logger.info("Loading LoRA adapter...")
                self.chat_model = PeftModel.from_pretrained(
                    base_model,
                    model_path,
                    torch_dtype=torch.float32
                )
                
                # Optional: Merge adapter with base model for faster inference
                # Uncomment the line below if you want to merge them permanently
                # self.chat_model = self.chat_model.merge_and_unload()
                
            else:
                # Original logic for full model
                logger.info("Loading as full model...")
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
                
                # Load full model
                self.chat_model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                    local_files_only=True,
                )
            
            self.chat_model.eval()
            logger.info("Chat model loaded successfully")
            
            # Load tokenizer - try from adapter path first, then base model
            logger.info("Loading tokenizer...")
            try:
                # First try loading from adapter directory
                self.chat_tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    local_files_only=True,
                )
                logger.info("Tokenizer loaded from adapter directory")
            except:
                # Fall back to base model tokenizer
                logger.info("Loading tokenizer from base model...")
                self.chat_tokenizer = AutoTokenizer.from_pretrained(
                    base_model_path if is_adapter else model_path,
                    trust_remote_code=True,
                    local_files_only=not is_adapter,
                )
                logger.info("Tokenizer loaded from base model")
            
            if self.chat_tokenizer.pad_token is None:
                self.chat_tokenizer.pad_token = self.chat_tokenizer.eos_token
            logger.info("Tokenizer loaded successfully")
            
            # Load sentiment model
            logger.info(f"Loading sentiment model from: {sentiment_path}")
            if not os.path.exists(sentiment_path):
                logger.warning(f"Sentiment model directory not found: {sentiment_path}")
                self.sentiment_pipeline = None
            else:
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
            logger.info(f"  Model Type: {'LoRA Adapter' if is_adapter else 'Full Model'}")
            logger.info(f"  Model Path: {model_path}")
            if is_adapter:
                logger.info(f"  Base Model: {base_model_path}")
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
        if not self.is_initialized or self.sentiment_pipeline is None:
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