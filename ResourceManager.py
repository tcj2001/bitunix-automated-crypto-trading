import contextlib
import asyncio
from typing import AsyncGenerator

class ResourceManager:
    @contextlib.asynccontextmanager
    async def managed_resources(self):
        resources = []
        try:
            yield resources
        finally:
            for resource in resources:
                await self.cleanup_resource(resource)

    async def cleanup_resource(self, resource):
    # For objects with a `close()` method
        if hasattr(resource, 'close'):
            if asyncio.iscoroutinefunction(resource.close):
                await resource.close()
            else:
                resource.close()
        # For objects with a `cleanup()` method
        elif hasattr(resource, 'cleanup'):
            if asyncio.iscoroutinefunction(resource.cleanup):
                await resource.cleanup()
            else:
                resource.cleanup()
        # For asyncio Tasks
        elif isinstance(resource, asyncio.Task):
            if not resource.done():
                resource.cancel()
                try:
                    await resource
                except asyncio.CancelledError:
                    pass
