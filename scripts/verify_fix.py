import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def test_api_fix():
    log("开始验证 API 修复情况...")
    
    # 1. 初始状态检查
    try:
        resp = requests.get(f"{BASE_URL}/api/config/providers")
        data = resp.json()
        initial_provider = data['current']
        log(f"初始提供商: {initial_provider}")
    except Exception as e:
        log(f"无法连接到 API: {e}", "ERROR")
        return

    # 2. 配置 Qwen API Key (测试修复点1：配置即切换)
    log("步骤 1: 配置 Qwen API Key...")
    try:
        payload = {"provider": "qwen", "api_key": "sk-test-qwen-key-123456"}
        resp = requests.post(f"{BASE_URL}/api/config/apikey", json=payload)
        result = resp.json()
        
        if result.get('success') and result.get('provider') == 'qwen':
            log("✔ API Key 配置成功")
        else:
            log(f"✘ 配置失败: {result}", "ERROR")
            
        # 立即检查当前提供商
        resp = requests.get(f"{BASE_URL}/api/config/providers")
        current = resp.json()['current']
        if current == 'qwen':
            log("✔ 验证通过：配置 Key 后自动切换为 [qwen]")
        else:
            log(f"✘ 验证失败：当前提供商仍为 [{current}]，预期为 [qwen]", "ERROR")
            
    except Exception as e:
        log(f"请求异常: {e}", "ERROR")

    # 3. 尝试切换到未配置的 Google (期望：失败且不切换)
    log("\n步骤 2: 尝试切换到未配置的 Google...")
    try:
        payload = {"provider": "google"}
        resp = requests.post(f"{BASE_URL}/api/llm/switch", json=payload)
        
        if resp.status_code != 200:
            log(f"✔ 正确拦截未配置的提供商 (Status: {resp.status_code})")
        else:
            log(f"✘ 异常：允许切换到未配置的提供商", "WARNING")
            
        # 检查是否保持在 qwen
        resp = requests.get(f"{BASE_URL}/api/config/providers")
        current = resp.json()['current']
        if current == 'qwen':
            log("✔ 验证通过：切换失败后保持在 [qwen]")
        else:
            log(f"✘ 验证失败：提供商变更为 [{current}]", "ERROR")
            
    except Exception as e:
        log(f"请求异常: {e}", "ERROR")

    # 4. 再次确认 Qwen 状态
    log("\n步骤 3: 最终状态确认...")
    resp = requests.get(f"{BASE_URL}/api/config/providers")
    providers = resp.json()['providers']
    qwen_status = next((p for p in providers if p['id'] == 'qwen'), None)
    
    if qwen_status and qwen_status['configured']:
         log("✔ Qwen 显示为 [已配置]")
    else:
         log("✘ Qwen 显示为 [未配置]", "ERROR")

    log("\n测试完成。")

if __name__ == "__main__":
    test_api_fix()
