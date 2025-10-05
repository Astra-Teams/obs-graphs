# Python Async Programming

Asynchronous programming in Python using `async` and `await`.

## Basic Example

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(main())
```

## Key Libraries

- `asyncio`: Built-in async runtime
- `aiohttp`: Async HTTP client/server
- `FastAPI`: Async web framework

Related: [[concurrency]], [[FastAPI]]
