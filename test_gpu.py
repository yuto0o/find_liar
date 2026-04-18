from llama_cpp import Llama

from .feature.config import MODEL_PATH

llm = Llama(model_path=MODEL_PATH, n_gpu_layers=40)

# n_gpu_layers を 1 以上（または -1 で全レイヤー）に設定

# 実行時のログに "BLAS = 1" または "CUDA0" といった記述があれば成功です
