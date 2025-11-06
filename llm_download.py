from huggingface_hub import snapshot_download

model_id = "jayayjay/TinyLlama-HealHub-FineTuned"
local_dir = "./models/healhub-tinyllama-1.1B-Chat"

# Download the entire model repository
snapshot_download(
    repo_id=model_id,
    local_dir=local_dir,
    local_dir_use_symlinks=False  # Better for direct file access
)