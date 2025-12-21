#!/usr/bin/env python3
"""
Quick verification script for RAG System setup
"""

import sys
import subprocess

def check_import(module_name, display_name=None):
    """Check if a Python module can be imported"""
    display_name = display_name or module_name
    try:
        __import__(module_name)
        print(f"✓ {display_name}")
        return True
    except ImportError as e:
        print(f"✗ {display_name}: {e}")
        return False

def main():
    print("🔍 Checking RAG System Dependencies\n")
    print("=" * 50)
    
    # Core dependencies
    print("\n📦 Core Packages:")
    results = []
    results.append(check_import("fastapi", "FastAPI"))
    results.append(check_import("uvicorn", "Uvicorn"))
    results.append(check_import("pydantic", "Pydantic"))
    results.append(check_import("pydantic_settings", "Pydantic Settings"))
    
    print("\n🔄 Task Queue:")
    results.append(check_import("celery", "Celery"))
    results.append(check_import("redis", "Redis"))
    
    print("\n📄 Document Processing:")
    results.append(check_import("fitz", "PyMuPDF"))
    results.append(check_import("langchain", "LangChain"))
    
    print("\n🤖 ML & Embeddings:")
    results.append(check_import("torch", "PyTorch"))
    results.append(check_import("sentence_transformers", "Sentence Transformers"))
    results.append(check_import("transformers", "Transformers"))
    
    print("\n🗄️ Vector Database:")
    results.append(check_import("faiss", "FAISS"))
    results.append(check_import("numpy", "NumPy"))
    
    print("\n🧪 Testing:")
    results.append(check_import("pytest", "pytest"))
    results.append(check_import("httpx", "HTTPX"))
    
    # Summary
    print("\n" + "=" * 50)
    total = len(results)
    passed = sum(results)
    print(f"\n📊 Summary: {passed}/{total} packages available")
    
    if passed == total:
        print("\n✅ All dependencies installed successfully!")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Start Celery: cd backend && celery -A src.tasks.celery_app worker --loglevel=info")
        print("3. Start Backend: cd backend && uvicorn src.main:app --reload --port 8000")
        return 0
    else:
        print(f"\n⚠️  {total - passed} dependencies missing. Run:")
        print("   ./quick-setup.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())
