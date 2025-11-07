import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel
from app.core.config import settings
import asyncio
from typing import Optional, List, Dict, Any
from functools import lru_cache

class MLService:
    def __init__(self):
        self.chat_model = None
        self.chat_tokenizer = None
        self.sentiment_pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    async def initialize(self):
        """Initialize ML models"""
        await asyncio.to_thread(self._load_models)
    
    def _load_models(self):
        # Load chat model
        print("Loading chat model...")
        base_model = AutoModelForCausalLM.from_pretrained(
            settings.MODEL_PATH,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto"
        )
        self.chat_model = PeftModel.from_pretrained(base_model, settings.MODEL_PATH)
        self.chat_tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_PATH)
        
        # Load sentiment analysis model
        print("Loading sentiment model...")
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=0 if self.device == "cuda" else -1
        )
        print("Models loaded successfully!")
    
    async def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        """Generate chat response"""
        # Build prompt
        prompt = "<|system|>\nYou are a helpful mental health support assistant.</s>\n"
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"<|user|>\n{content}</s>\n"
            else:
                prompt += f"<|assistant|>\n{content}</s>\n"
        prompt += "<|assistant|>\n"
        
        # Generate response
        response = await asyncio.to_thread(self._generate, prompt)
        return response
    
    def _generate(self, prompt: str) -> str:
        inputs = self.chat_tokenizer(prompt, return_tensors="pt").to(self.chat_model.device)
        with torch.no_grad():
            outputs = self.chat_model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.chat_tokenizer.eos_token_id
            )
        response = self.chat_tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extract only the assistant's response
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
        return response
    
    async def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        result = await asyncio.to_thread(self.sentiment_pipeline, text)
        sentiment = result[0]
        # Convert to -1 to 1 scale
        score = sentiment['score'] if sentiment['label'] == 'POSITIVE' else -sentiment['score']
        return {
            "label": sentiment['label'],
            "score": score
        }
    
    async def calculate_risk_score(self, text: str, sentiment_score: float) -> float:
        """Calculate mental health risk score"""
        # Keywords indicating potential risk
        high_risk_keywords = ['suicide', 'kill myself', 'end it all', 'no point', 'hopeless']
        medium_risk_keywords = ['depressed', 'anxious', 'panic', 'scared', 'alone', 'worthless']
        
        text_lower = text.lower()
        risk_score = 0.0
        
        # Keyword-based scoring
        for keyword in high_risk_keywords:
            if keyword in text_lower:
                risk_score += 0.3
        
        for keyword in medium_risk_keywords:
            if keyword in text_lower:
                risk_score += 0.1
        
        # Sentiment-based adjustment
        if sentiment_score < -0.5:
            risk_score += 0.2
        elif sentiment_score < -0.3:
            risk_score += 0.1
        
        return min(risk_score, 1.0)  # Cap at 1.0

# Global ML service instance
ml_service = MLService()