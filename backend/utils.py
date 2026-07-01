# ===== LLM configuration: OpenAI SDK pointed at OpenRouter =====
# Use the OPENROUTER_API_KEY the user put in the project's .env (NOT an ambient
# OS OPENAI_API_KEY). The .env is loaded explicitly below.
import os
from pathlib import Path

if not os.getenv("MARKET_DISABLE_LLM"):
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    except Exception:
        pass

openai_api_key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
openai_api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
gpt_chat_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
gpt_embedding_model = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

# Put your name
key_owner = "HJO"

# Absolute paths (repo root = backend/utils.py's parents[1]) so the maze data
# loads regardless of the process CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
maze_assets_loc = str(_REPO_ROOT / "environment/frontend_server/static_dirs/assets")
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

fs_storage = str(_REPO_ROOT / "environment/frontend_server/storage")
fs_temp_storage = str(_REPO_ROOT / "environment/frontend_server/temp_storage")

collision_block_id = "32125"

# Verbose
debug = True
