from transformers import AutoTokenizer, AutoModelForSequenceClassification

SENTIMENT_MODEL_PATH = "./models/sentiment_model/"

# Download and save the model and tokenizer locally
model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")

# Save to your specified local path
model.save_pretrained(SENTIMENT_MODEL_PATH)
tokenizer.save_pretrained(SENTIMENT_MODEL_PATH)

print(f"Model saved to: {SENTIMENT_MODEL_PATH}")