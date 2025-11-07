#!/usr/bin/env python3
"""Test script to verify SSE stream format from FastAPI backend."""

import asyncio
import json
import sys

import httpx


async def test_chat_stream():
    """Test the chat endpoint and verify SSE format."""
    url = "http://127.0.0.1:8001/api/chat"
    payload = {
        "message": "Hello, how are you?",
        "threadId": "test-thread-123",
        "config": None,
    }

    print("Testing chat stream format...")
    print(f"Sending request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}\n")

                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    print(await response.aread())
                    return False

                chunk_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_count += 1
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(data_str)
                            print(f"\n--- Chunk {chunk_count} ---")
                            print(json.dumps(chunk, indent=2))

                            # Verify format
                            if "event" in chunk:
                                event = chunk["event"]
                                data = chunk.get("data")

                                if event == "messages/partial":
                                    if not isinstance(data, list):
                                        print(f"❌ ERROR: messages/partial data should be array, got {type(data)}")
                                        return False
                                    print(f"✅ Valid messages/partial event with {len(data)} message(s)")

                                elif event == "updates":
                                    if not isinstance(data, dict):
                                        print(f"❌ ERROR: updates data should be dict, got {type(data)}")
                                        return False
                                    node_names = list(data.keys())
                                    print(f"✅ Valid updates event for nodes: {node_names}")

                                elif event == "error":
                                    print(f"⚠️  Error event received: {data}")

                                else:
                                    print(f"❓ Unknown event type: {event}")
                            else:
                                print(f"❌ ERROR: Chunk missing 'event' key")
                                return False

                        except json.JSONDecodeError as e:
                            print(f"❌ ERROR: Failed to parse JSON: {e}")
                            print(f"Raw data: {data_str}")
                            return False

                print(f"\n✅ Test completed successfully! Received {chunk_count} chunks.")
                return True

        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(test_chat_stream())
    sys.exit(0 if result else 1)
