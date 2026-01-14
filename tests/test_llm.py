"""LLM 集成测试"""

import asyncio
import os
import sys

# 确保从项目根目录运行
os.chdir("/Users/dxx/Coding/stock_trading")
sys.path.insert(0, "/Users/dxx/Coding/stock_trading")

# 预加载 dotenv
from dotenv import load_dotenv
load_dotenv()

from src.ai.llm import create_llm, get_default_llm, LLMMessage
from src.ai.llm.base import MessageRole, LLMConfig
from src.config import LLMProvider


async def test_gemini():
    """测试 Gemini LLM"""
    print("\n" + "=" * 50)
    print("测试 Gemini LLM")
    print("=" * 50)
    
    try:
        llm = create_llm(provider=LLMProvider.GOOGLE)
        print(f"创建 LLM 实例: {llm}")
        
        # 简单对话测试
        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的量化分析师，回答要简洁专业。"
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="请用一句话解释什么是 MACD 指标？"
            ),
        ]
        
        print("\n发送请求...")
        response = await llm.chat(messages)
        
        print(f"\n模型: {response.model}")
        print(f"内容: {response.content}")
        print(f"Token 用量: {response.usage}")
        
        print("\n✅ Gemini 测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ Gemini 测试失败: {e}")
        return False


async def test_streaming():
    """测试流式输出"""
    print("\n" + "=" * 50)
    print("测试流式输出")
    print("=" * 50)
    
    try:
        llm = get_default_llm()
        
        messages = [
            LLMMessage(
                role=MessageRole.USER,
                content="用 3 个要点说明技术分析的核心原则。"
            ),
        ]
        
        print("\n流式响应:")
        async for chunk in llm.chat_stream(messages):
            print(chunk, end="", flush=True)
        
        print("\n\n✅ 流式输出测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 流式输出测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("\n🚀 开始 LLM 集成测试\n")
    
    results = []
    
    # 测试 Gemini
    results.append(await test_gemini())
    
    # 测试流式输出
    results.append(await test_streaming())
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试汇总")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败")


if __name__ == "__main__":
    asyncio.run(main())
