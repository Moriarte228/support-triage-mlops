import time

import boto3

MODEL_ID = "eu.amazon.nova-lite-v1:0"

client = boto3.client("bedrock-runtime", region_name="eu-north-1")
start = time.perf_counter()
resp = client.converse(
    modelId=MODEL_ID,
    system=[{"text": "You are a support assistant for a fictional bank."}],
    messages=[{"role": "user", "content": [{"text": "My card hasn't arrived yet. What should I do? Answer in two sentences."}]}],
    inferenceConfig={"maxTokens": 200, "temperature": 0.2},
)
print(resp["output"]["message"]["content"][0]["text"])
print(resp["usage"], f"{time.perf_counter() - start:.2f}s")